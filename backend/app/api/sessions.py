# backend/app/api/sessions.py
"""
Sessions router — US9, US11, US12, US13.

Endpoints:
  POST   /api/sessions/                      create & start a game session (US4, US6)
  GET    /api/sessions/{match_id}            get current session state (US7, US12)
  POST   /api/sessions/{match_id}/turn       submit a human player's argument (US9)
  POST   /api/sessions/{match_id}/objection  submit an objection (US11)
  POST   /api/sessions/{match_id}/verdict    submit a human judge verdict (US13)
  DELETE /api/sessions/{match_id}            quit / abandon the game session
  GET    /api/sessions/{match_id}/transcript  get full debate transcript
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.match import Match, MatchStatus, PlayerRole
from app.models.game_session import GameSession
from app.models.round import Round
from app.models.user import User
from app.schemas.session import (
    ObjectionResponse,
    RoundCreate,
    RoundOut,
    SessionCreate,
    VerdictCreate,
)
from app.services.game_service import (
    advance_one_ai_turn,
    get_game_state,
    quit_game,
    start_game,
    submit_objection,
    submit_player_turn,
    submit_player_verdict,
)

router = APIRouter(prefix="/api/sessions", tags=["Sessions"])


# ── POST /api/sessions/ — Create & start game session ─────────────────────────

@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    summary="US4 + US6 — Start a game session: generate case, distribute evidence, begin trial",
)
async def create_session(
    body: SessionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Creates and starts a game session for an existing match.

    1. Triggers AI Clerk case generation (US4)
    2. Distributes role-specific evidence (US6)
    3. Creates the GameSession record
    4. Auto-progresses AI turns until the human player needs to act
    5. Returns the full game state including case summary, evidence, and transcript

    The match must be in LOBBY status and belong to the authenticated user.
    """
    # Validate match
    result = await db.execute(
        select(Match).where(
            Match.id == body.match_id,
            Match.player_id == current_user.id,
        )
    )
    match = result.scalar_one_or_none()
    if match is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match not found",
        )
    if match.status != MatchStatus.LOBBY:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Match is already in '{match.status.value}' status. Only LOBBY matches can be started.",
        )

    # Check if a session already exists
    existing = await db.execute(
        select(GameSession).where(GameSession.match_id == body.match_id)
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A game session already exists for this match",
        )

    try:
        game_state = await start_game(match, db)
        return game_state
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start game session: {str(e)}",
        )


# ── GET /api/sessions/{match_id} — Get session state ──────────────────────────

@router.get(
    "/{match_id}",
    summary="US7 + US12 — Get current session state including Scales of Justice",
)
async def get_session(
    match_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns the full game state:
    - Case summary (US7)
    - Current round, whose turn, scales value (US12)
    - Full debate transcript
    - Verdict (if completed, US13)
    - What the frontend should show next (waiting_for)
    """
    # Verify ownership
    result = await db.execute(
        select(Match).where(
            Match.id == match_id,
            Match.player_id == current_user.id,
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match not found",
        )

    try:
        game_state = await get_game_state(match_id, db)
        return game_state
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


# ── POST /api/sessions/{match_id}/turn — Submit human argument ────────────────

@router.post(
    "/{match_id}/turn",
    summary="US9 — Submit a human player's argument with optional attached evidence",
)
async def submit_turn(
    match_id: uuid.UUID,
    body: RoundCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    US9: A player selects an evidence card and attaches it to their argument draft,
    so that they can submit a valid, fact-based argument to the court.

    After submission:
    1. The human turn is validated and recorded
    2. Used evidence is marked (US10)
    3. AI actors auto-progress until the next human pause point
    4. Returns updated game state with new transcript entries
    """
    # Verify ownership
    result = await db.execute(
        select(Match).where(
            Match.id == match_id,
            Match.player_id == current_user.id,
        )
    )
    match = result.scalar_one_or_none()
    if match is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match not found",
        )
    if match.status not in {MatchStatus.IN_PROGRESS, MatchStatus.LOBBY}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Match is in '{match.status.value}' status. Cannot submit turns.",
        )

    try:
        game_state = await submit_player_turn(
            match_id=match_id,
            argument_text=body.argument_text,
            evidence_id=body.attached_evidence_id,
            db=db,
        )
        return game_state
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


# ── POST /api/sessions/{match_id}/advance — Spectator turn-by-turn ───────────

@router.post(
    "/{match_id}/advance",
    summary="Advance one AI turn — for spectator/judge roles watching the debate live",
)
async def advance_turn(
    match_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Process exactly one AI turn and return the updated game state.
    The frontend calls this in a loop for spectator and judge roles so that
    messages appear one at a time rather than all at once.
    """
    result = await db.execute(
        select(Match).where(
            Match.id == match_id,
            Match.player_id == current_user.id,
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found")

    try:
        game_state = await advance_one_ai_turn(match_id, db)
        return game_state
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ── POST /api/sessions/{match_id}/objection — Objection mechanic ─────────────

@router.post(
    "/{match_id}/objection",
    summary="US11 — Raise a one-time objection against the opponent's last argument",
)
async def raise_objection(
    match_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    US11: One-click objection. No message required.
    Each side (prosecution / defense) may raise exactly one objection per session.

    The opponent's most recent argument is flagged. On their next AI turn,
    the engine injects a court notice forcing them to address the challenge.
    Returns the updated game state (including objection_available: false).
    """
    result = await db.execute(
        select(Match).where(
            Match.id == match_id,
            Match.player_id == current_user.id,
        )
    )
    match = result.scalar_one_or_none()
    if match is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found")

    try:
        game_state = await submit_objection(match_id, match.player_role, db)
        return game_state
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ── POST /api/sessions/{match_id}/verdict — Human judge verdict ───────────────

@router.post(
    "/{match_id}/verdict",
    summary="US13 — Submit a human judge's final verdict",
)
async def submit_verdict(
    match_id: uuid.UUID,
    body: VerdictCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    US13: The Judge ends the trial, analyzes the chat history alongside the
    Scales of Justice, and generates a motivated final verdict saved to the database.

    Only available when the player's role is Judge and it's the verdict phase.
    """
    # Verify ownership and role
    result = await db.execute(
        select(Match).where(
            Match.id == match_id,
            Match.player_id == current_user.id,
        )
    )
    match = result.scalar_one_or_none()
    if match is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match not found",
        )

    if match.player_role != PlayerRole.JUDGE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the Judge can submit a verdict",
        )

    try:
        is_guilty = body.verdict == "guilty"
        game_state = await submit_player_verdict(
            match_id=match_id,
            guilty=is_guilty,
            reasoning=body.verdict_reasoning,
            prosecution_score=None,
            defense_score=None,
            db=db,
        )
        return game_state
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


# ── DELETE /api/sessions/{match_id} — Quit game ──────────────────────────────

@router.delete(
    "/{match_id}",
    status_code=status.HTTP_200_OK,
    summary="Quit / abandon the game session",
)
async def delete_session(
    match_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Quit the current game session. The match is marked as abandoned."""
    # Verify ownership
    result = await db.execute(
        select(Match).where(
            Match.id == match_id,
            Match.player_id == current_user.id,
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match not found",
        )

    try:
        game_state = await quit_game(match_id, db)
        return game_state
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


# ── GET /api/sessions/{match_id}/transcript — Full transcript ─────────────────

@router.get(
    "/{match_id}/transcript",
    response_model=list[RoundOut],
    summary="Get the full debate transcript as a list of rounds",
)
async def get_transcript(
    match_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[RoundOut]:
    """Returns all rounds for the match's game session, ordered by round number."""
    # Verify ownership
    result = await db.execute(
        select(Match).where(
            Match.id == match_id,
            Match.player_id == current_user.id,
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match not found",
        )

    # Find the session
    session_result = await db.execute(
        select(GameSession).where(GameSession.match_id == match_id)
    )
    session = session_result.scalar_one_or_none()
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No game session found for this match",
        )

    # Get all rounds
    rounds_result = await db.execute(
        select(Round)
        .where(Round.game_session_id == session.id)
        .order_by(Round.round_number)
    )
    rounds = rounds_result.scalars().all()
    return [RoundOut.model_validate(r) for r in rounds]
