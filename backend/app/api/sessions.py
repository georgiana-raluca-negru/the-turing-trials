# backend/app/api/sessions.py
"""
Game session router — US9, US10, US11, US12, US13.

Endpoints:
  POST /api/sessions                          start a session for a match
  GET  /api/sessions/{session_id}             full session state
  GET  /api/sessions/{session_id}/scales      Scales of Justice — US12
  POST /api/sessions/{session_id}/rounds      submit argument + evidence — US9
  POST /api/sessions/{session_id}/objection   trigger objection — US11
  POST /api/sessions/{session_id}/verdict     end trial + save verdict — US13
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.evidence import Evidence
from app.models.game_session import GameSession
from app.models.match import Match, MatchStatus, PlayerRole, Verdict
from app.models.round import Round, RoundSpeaker
from app.models.user import User
from app.schemas.session import (
    ObjectionCreate,
    ObjectionResponse,
    RoundCreate,
    RoundOut,
    ScalesOut,
    SessionCreate,
    SessionOut,
    VerdictCreate,
    VerdictOut,
)

router = APIRouter(prefix="/api/sessions", tags=["Game Sessions"])


# ── Start a session ───────────────────────────────────────────────────────────

@router.post(
    "/",
    response_model=SessionOut,
    status_code=status.HTTP_201_CREATED,
    summary="Start a new game session for a match",
)
async def start_session(
    body: SessionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SessionOut:
    match = await _get_match_or_404(body.match_id, current_user.id, db)

    if match.status != MatchStatus.LOBBY:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A session can only be started for a match in LOBBY status",
        )

    # Determine who goes first based on the player's role
    first_turn = _first_turn(match.player_role)

    session = GameSession(
        match_id=match.id,
        max_rounds=body.max_rounds,
        current_round=1,
        current_turn=first_turn,
        scales_value=0.0,
    )
    db.add(session)

    match.status = MatchStatus.IN_PROGRESS
    await db.commit()
    await db.refresh(session)
    return SessionOut.model_validate(session)


# ── Get session state ─────────────────────────────────────────────────────────

@router.get(
    "/{session_id}",
    response_model=SessionOut,
    summary="Get full session state",
)
async def get_session(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SessionOut:
    session = await _get_session_or_404(session_id, current_user.id, db)
    return SessionOut.model_validate(session)


# ── US12 — Scales of Justice ──────────────────────────────────────────────────

@router.get(
    "/{session_id}/scales",
    response_model=ScalesOut,
    summary="US12 — Get the current Scales of Justice value",
)
async def get_scales(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ScalesOut:
    """
    US12: As a player, I want a visual Scales of Justice progress bar that
    tilts toward me or my opponent after each round so I can monitor the
    match score in real-time.
    """
    session = await _get_session_or_404(session_id, current_user.id, db)
    return ScalesOut(
        session_id=session.id,
        scales_value=session.scales_value,
        current_round=session.current_round,
        max_rounds=session.max_rounds,
        current_turn=session.current_turn,
    )


# ── US9 — Submit a round argument ─────────────────────────────────────────────

@router.post(
    "/{session_id}/rounds",
    response_model=RoundOut,
    status_code=status.HTTP_201_CREATED,
    summary="US9 — Submit an argument and optionally attach an evidence card",
)
async def submit_round(
    session_id: uuid.UUID,
    body: RoundCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RoundOut:
    """
    US9:  Player selects an evidence card and attaches it to their argument.
    US10: The attached evidence card is marked is_used=True after this round.
    """
    session = await _get_session_or_404(session_id, current_user.id, db)
    match = await _get_match_or_404(session.match_id, current_user.id, db)

    if match.status != MatchStatus.IN_PROGRESS:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This session is not in progress",
        )

    # Validate and mark evidence card as used (US10)
    if body.attached_evidence_id is not None:
        ev_result = await db.execute(
            select(Evidence).where(
                Evidence.id == body.attached_evidence_id,
                Evidence.match_id == session.match_id,
            )
        )
        evidence: Evidence | None = ev_result.scalar_one_or_none()

        if evidence is None:
            raise HTTPException(status_code=404, detail="Evidence card not found in this match")
        if evidence.is_used:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This evidence card has already been used (US10)",
            )

        # Mark as used (US10)
        evidence.is_used = True
        evidence.used_in_round = session.current_round

    # Create the round record
    round_record = Round(
        game_session_id=session.id,
        round_number=session.current_round,
        speaker=_role_to_speaker(match.player_role),
        argument_text=body.argument_text,
        attached_evidence_id=body.attached_evidence_id,
    )
    db.add(round_record)

    # Advance turn and round counter
    session.current_turn = _next_turn(session.current_turn)
    if session.current_turn == _first_turn(match.player_role):
        # Both sides have spoken — increment round
        session.current_round += 1

    session.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(round_record)
    return RoundOut.model_validate(round_record)


# ── US11 — Objection ──────────────────────────────────────────────────────────

@router.post(
    "/{session_id}/objection",
    response_model=ObjectionResponse,
    summary="US11 — Trigger an objection during the opponent's turn",
)
async def raise_objection(
    session_id: uuid.UUID,
    body: ObjectionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ObjectionResponse:
    """
    US11: As a player, I want an Objection button active only during my
    opponent's turn so I can pause their text generation and input a reason.

    The round referenced by *round_id* must belong to this session and must
    NOT already have been objected to.
    The AI rebuttal/sustain logic will be wired here when the LangGraph
    agent is available. For now the objection is recorded and a stub
    response is returned.
    """
    session = await _get_session_or_404(session_id, current_user.id, db)

    result = await db.execute(
        select(Round).where(
            Round.id == body.round_id,
            Round.game_session_id == session.id,
        )
    )
    round_record: Round | None = result.scalar_one_or_none()

    if round_record is None:
        raise HTTPException(status_code=404, detail="Round not found in this session")
    if round_record.was_objected:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This round has already been objected to",
        )

    # Record the objection
    round_record.was_objected = True
    round_record.objection_text = body.objection_text
    # TODO: call AI Judge agent to generate objection_response
    round_record.objection_response = (
        "[AI response pending — LangGraph agent not yet wired]"
    )

    await db.commit()

    return ObjectionResponse(
        round_id=round_record.id,
        objection_accepted=True,   # placeholder until AI decides
        objection_response=round_record.objection_response,
    )


# ── US13 — Verdict ────────────────────────────────────────────────────────────

@router.post(
    "/{session_id}/verdict",
    response_model=VerdictOut,
    summary="US13 — Judge ends the trial and saves the final verdict",
)
async def submit_verdict(
    session_id: uuid.UUID,
    body: VerdictCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> VerdictOut:
    """
    US13: As the Judge, I want to end the trial after a predefined number
    of rounds, analyze the chat history alongside the Scales of Justice,
    and generate a motivated final verdict (Guilty / Not Guilty) saved to
    the database.
    """
    session = await _get_session_or_404(session_id, current_user.id, db)
    match = await _get_match_or_404(session.match_id, current_user.id, db)

    if match.status != MatchStatus.IN_PROGRESS:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Trial is not currently in progress",
        )

    # Only the Judge role can submit a verdict
    if match.player_role != PlayerRole.JUDGE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the Judge can submit a verdict",
        )

    now = datetime.now(timezone.utc)

    # Persist verdict on match
    match.verdict = Verdict(body.verdict)
    match.verdict_reasoning = body.verdict_reasoning
    match.status = MatchStatus.COMPLETED
    match.completed_at = now

    # Update win stat for the player (US3 dashboard)
    # Judge wins if they successfully delivered a reasoned verdict
    current_user.total_wins += 1

    await db.commit()

    return VerdictOut(
        match_id=match.id,
        verdict=match.verdict.value,
        verdict_reasoning=match.verdict_reasoning,
        scales_final=session.scales_value,
        completed_at=now,
    )


# ── Internal helpers ──────────────────────────────────────────────────────────

async def _get_session_or_404(
    session_id: uuid.UUID, player_id: uuid.UUID, db: AsyncSession
) -> GameSession:
    result = await db.execute(
        select(GameSession)
        .join(Match, GameSession.match_id == Match.id)
        .where(GameSession.id == session_id, Match.player_id == player_id)
    )
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return session


async def _get_match_or_404(
    match_id: uuid.UUID, player_id: uuid.UUID, db: AsyncSession
) -> Match:
    result = await db.execute(
        select(Match).where(Match.id == match_id, Match.player_id == player_id)
    )
    match = result.scalar_one_or_none()
    if match is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found")
    return match


def _role_to_speaker(role: PlayerRole) -> RoundSpeaker:
    mapping = {
        PlayerRole.DEFENSE_ATTORNEY: RoundSpeaker.PLAYER,
        PlayerRole.PROSECUTOR:       RoundSpeaker.PLAYER,
        PlayerRole.JUDGE:            RoundSpeaker.AI_JUDGE,
        PlayerRole.SPECTATOR:        RoundSpeaker.PLAYER,
    }
    return mapping.get(role, RoundSpeaker.PLAYER)


def _first_turn(role: PlayerRole) -> str:
    """Defense always opens the arguments."""
    return PlayerRole.DEFENSE_ATTORNEY.value


def _next_turn(current: str | None) -> str:
    if current == PlayerRole.DEFENSE_ATTORNEY.value:
        return PlayerRole.PROSECUTOR.value
    return PlayerRole.DEFENSE_ATTORNEY.value
