# backend/app/services/game_service.py
"""
Game orchestration service — bridges the FastAPI backend with the
backend_integration contract layer.

Responsibilities:
  - Translate between ORM models and backend_integration runtime objects
  - Call the shared interface for match lifecycle operations
  - Sync results back to the database (Match, GameSession, Round, Evidence)
  - Manage the in-memory game store
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend_integration.interface import (
    create_match as bi_create_match,
    get_available_evidence,
    progress_match as bi_progress_one_turn,
    progress_until_human_or_terminal,
    quit_match as bi_quit_match,
    submit_human_turn as bi_submit_human_turn,
    submit_human_verdict as bi_submit_human_verdict,
)
from backend_integration.models.actors import ActorConfiguration, ActorController, ActorRole
from backend_integration.models.case_file import CaseFileBundle
from backend_integration.models.match import (
    MatchConfig,
    MatchRuntimeState,
    MatchStatus as BiMatchStatus,
    ProgressAction,
)
from backend_integration.models.turns import HumanJudgeVerdictInput, HumanTurnInput, TurnRecord

from app.models.evidence import Evidence, EvidenceRole
from app.models.game_session import GameSession
from app.models.match import Match, MatchStatus, PlayerRole, Verdict
from app.models.round import Round, RoundSpeaker
from app.models.user import User
from app.services.game_store import game_store


# ── Actor mapping from PlayerRole ─────────────────────────────────────────────
# The player's chosen role determines which actors are human vs AI.

def _build_actor_config(player_role: PlayerRole) -> ActorConfiguration:
    """
    Map the human player's chosen role to an ActorConfiguration.

    | PlayerRole         | prosecution | defense | judge |
    |--------------------|-------------|---------|-------|
    | defense_attorney   | AI          | HUMAN   | AI    |
    | prosecutor         | HUMAN       | AI      | AI    |
    | judge              | AI          | AI      | HUMAN |
    | spectator          | AI          | AI      | AI    |
    """
    mapping = {
        PlayerRole.DEFENSE_ATTORNEY: ActorConfiguration(
            prosecution=ActorController.AI,
            defense=ActorController.HUMAN,
            judge=ActorController.AI,
        ),
        PlayerRole.PROSECUTOR: ActorConfiguration(
            prosecution=ActorController.HUMAN,
            defense=ActorController.AI,
            judge=ActorController.AI,
        ),
        PlayerRole.JUDGE: ActorConfiguration(
            prosecution=ActorController.AI,
            defense=ActorController.AI,
            judge=ActorController.HUMAN,
        ),
        PlayerRole.SPECTATOR: ActorConfiguration(
            prosecution=ActorController.AI,
            defense=ActorController.AI,
            judge=ActorController.AI,
        ),
    }
    return mapping[player_role]


def _player_role_to_actor_role(player_role: PlayerRole) -> ActorRole | None:
    """Map the player's role to the ActorRole they control (None for spectator)."""
    mapping = {
        PlayerRole.DEFENSE_ATTORNEY: ActorRole.DEFENSE,
        PlayerRole.PROSECUTOR: ActorRole.PROSECUTION,
        PlayerRole.JUDGE: ActorRole.JUDGE,
    }
    return mapping.get(player_role)


# ── Start game ────────────────────────────────────────────────────────────────

async def start_game(match: Match, db: AsyncSession) -> dict[str, Any]:
    """
    Start a game session for a match.

    1. Build MatchConfig + ActorConfiguration from the Match ORM object
    2. Call backend_integration.create_match() → generates case file via AI Clerk
    3. Persist evidence cards to DB
    4. Create GameSession in DB
    5. Auto-progress AI turns until human pause point
    6. Save runtime state to in-memory store
    7. Return the current game state

    Returns a dict with session info, evidence, transcript, and scales.
    """
    match_id_str = str(match.id)

    # 1. Build configuration
    config = MatchConfig(
        match_id=match_id_str,
        user_prompt=match.player_prompt,
        max_rounds=match.total_rounds or 3,
        allow_evidence_reuse=False,
    )
    actors = _build_actor_config(match.player_role)

    # 2. Create match via backend_integration (triggers AI Clerk)
    runtime_state = bi_create_match(config=config, actors=actors)

    # 3. Persist evidence to DB
    await _persist_evidence(match.id, runtime_state.case_file, db)

    # 4. Persist case file JSON and summary to Match
    case_file_dict = runtime_state.case_file.model_dump()
    match.case_file_json = json.dumps(case_file_dict, ensure_ascii=False)
    match.case_summary = (
        f"{runtime_state.case_file.summary.crime}: "
        f"{', '.join(runtime_state.case_file.summary.charges)}"
    )
    match.status = MatchStatus.IN_PROGRESS

    # Increment total_matches now that the game is actually starting
    player = await db.get(User, match.player_id)
    if player:
        player.total_matches += 1

    # 5. Create GameSession in DB
    session = GameSession(
        match_id=match.id,
        current_round=runtime_state.current_cycle,
        max_rounds=config.max_rounds,
        current_turn=runtime_state.next_actor.value if runtime_state.next_actor else None,
        scales_value=0.0,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    # 6. For judge/spectator roles the frontend drives turn-by-turn via /advance.
    #    For playing roles, auto-progress until the human needs to act.
    if match.player_role not in {PlayerRole.JUDGE, PlayerRole.SPECTATOR}:
        result = progress_until_human_or_terminal(state=runtime_state)
        runtime_state = result.state
        await _sync_transcript_to_db(session.id, runtime_state, db)
        await _sync_session_state(session, runtime_state, db)
        if result.action == ProgressAction.MATCH_COMPLETED:
            await _finalize_match(match, runtime_state, db)

    await db.commit()

    # 7. Save runtime state to in-memory store
    game_store.save(match_id_str, runtime_state)

    return _build_game_state_response(match, session, runtime_state)


# ── Progress game ─────────────────────────────────────────────────────────────

async def progress_game(match_id: uuid.UUID, db: AsyncSession) -> dict[str, Any]:
    """
    Progress the game by running AI turns until the next human pause point.
    Used after a human turn is submitted to continue the AI's responses.
    """
    match_id_str = str(match_id)
    runtime_state = game_store.get(match_id_str)
    if runtime_state is None:
        raise ValueError(f"No active game session for match {match_id}")

    result = progress_until_human_or_terminal(state=runtime_state)
    runtime_state = result.state

    # Sync to DB
    match = await db.get(Match, match_id)
    if match is None:
        raise ValueError(f"Match {match_id} not found")

    session_result = await db.execute(
        select(GameSession).where(GameSession.match_id == match_id)
    )
    session = session_result.scalar_one_or_none()
    if session is None:
        raise ValueError(f"No GameSession for match {match_id}")

    await _sync_transcript_to_db(session.id, runtime_state, db)
    await _sync_session_state(session, runtime_state, db)

    if result.action == ProgressAction.MATCH_COMPLETED:
        await _finalize_match(match, runtime_state, db)

    await db.commit()
    game_store.save(match_id_str, runtime_state)

    return _build_game_state_response(match, session, runtime_state)


# ── Submit human turn ─────────────────────────────────────────────────────────

async def submit_player_turn(
    match_id: uuid.UUID,
    argument_text: str,
    evidence_id: uuid.UUID | None,
    db: AsyncSession,
) -> dict[str, Any]:
    """
    Submit a human player's argument turn, then auto-progress AI actors.
    """
    match_id_str = str(match_id)
    runtime_state = game_store.get(match_id_str)
    if runtime_state is None:
        raise ValueError(f"No active game session for match {match_id}")

    match = await db.get(Match, match_id)
    if match is None:
        raise ValueError(f"Match {match_id} not found")

    # Determine the actor role for this player
    actor_role = _player_role_to_actor_role(match.player_role)
    if actor_role is None:
        raise ValueError("Spectators cannot submit turns")

    # Build evidence IDs list
    evidence_ids: list[str] = []
    if evidence_id is not None:
        # Map DB evidence UUID to the runtime evidence code
        evidence_code = await _get_evidence_code(
            evidence_id, match_id, runtime_state, db
        )
        if evidence_code:
            evidence_ids.append(evidence_code)

    # Submit via backend_integration
    human_input = HumanTurnInput(
        actor_role=actor_role,
        text=argument_text,
        attached_evidence_ids=evidence_ids,
    )
    result = bi_submit_human_turn(state=runtime_state, human_turn=human_input)
    runtime_state = result.state

    # Mark evidence as used in DB
    if evidence_id is not None:
        await _mark_evidence_used_in_db(evidence_id, db)

    # Auto-progress AI turns
    if result.action in {ProgressAction.HUMAN_TURN_COMPLETED, ProgressAction.AI_TURN_COMPLETED}:
        progress_result = progress_until_human_or_terminal(state=runtime_state)
        runtime_state = progress_result.state
        result = progress_result

    # Sync to DB
    session_result = await db.execute(
        select(GameSession).where(GameSession.match_id == match_id)
    )
    session = session_result.scalar_one_or_none()
    if session is None:
        raise ValueError(f"No GameSession for match {match_id}")

    await _sync_transcript_to_db(session.id, runtime_state, db)
    await _sync_session_state(session, runtime_state, db)

    if result.action == ProgressAction.MATCH_COMPLETED:
        await _finalize_match(match, runtime_state, db)

    await db.commit()
    game_store.save(match_id_str, runtime_state)

    return _build_game_state_response(match, session, runtime_state)


# ── Submit human verdict ──────────────────────────────────────────────────────

async def submit_player_verdict(
    match_id: uuid.UUID,
    guilty: bool,
    reasoning: str,
    prosecution_score: int | None,
    defense_score: int | None,
    db: AsyncSession,
) -> dict[str, Any]:
    """
    Submit a human judge's verdict.
    """
    match_id_str = str(match_id)
    runtime_state = game_store.get(match_id_str)
    if runtime_state is None:
        raise ValueError(f"No active game session for match {match_id}")

    verdict_input = HumanJudgeVerdictInput(
        guilty=guilty,
        reasoning=reasoning,
        prosecution_score=prosecution_score,
        defense_score=defense_score,
    )
    result = bi_submit_human_verdict(state=runtime_state, human_verdict=verdict_input)
    runtime_state = result.state

    # Sync to DB
    match = await db.get(Match, match_id)
    if match is None:
        raise ValueError(f"Match {match_id} not found")

    session_result = await db.execute(
        select(GameSession).where(GameSession.match_id == match_id)
    )
    session = session_result.scalar_one_or_none()
    if session is None:
        raise ValueError(f"No GameSession for match {match_id}")

    await _sync_transcript_to_db(session.id, runtime_state, db)
    await _sync_session_state(session, runtime_state, db)
    await _finalize_match(match, runtime_state, db)

    await db.commit()
    game_store.save(match_id_str, runtime_state)

    return _build_game_state_response(match, session, runtime_state)


# ── Quit game ─────────────────────────────────────────────────────────────────

async def quit_game(match_id: uuid.UUID, db: AsyncSession) -> dict[str, Any]:
    """Quit / abandon an active game session."""
    match_id_str = str(match_id)
    runtime_state = game_store.get(match_id_str)

    match = await db.get(Match, match_id)
    if match is None:
        raise ValueError(f"Match {match_id} not found")

    if runtime_state is not None:
        result = bi_quit_match(state=runtime_state, reason="Player quit the match.")
        runtime_state = result.state
        game_store.save(match_id_str, runtime_state)

    match.status = MatchStatus.ABANDONED
    match.completed_at = datetime.now(timezone.utc)

    session_result = await db.execute(
        select(GameSession).where(GameSession.match_id == match_id)
    )
    session = session_result.scalar_one_or_none()

    await db.commit()

    if session and runtime_state:
        return _build_game_state_response(match, session, runtime_state)
    return {"match_id": match_id_str, "status": "abandoned"}


# ── Submit objection ─────────────────────────────────────────────────────────

async def submit_objection(
    match_id: uuid.UUID,
    player_role: PlayerRole,
    db: AsyncSession,
) -> dict[str, Any]:
    """
    US11 — Record an objection against the opponent's most recent argument.

    Each side (prosecution / defense) may only raise one objection per session.
    When accepted, the target TurnRecord gets system_note="[OBJECTION RAISED]"
    so that the AI engine's adapter injects a court notice into the next turn's
    history, forcing the opponent to address the challenge.
    """
    match_id_str = str(match_id)
    runtime_state = game_store.get(match_id_str)
    if runtime_state is None:
        raise ValueError(f"No active game session for match {match_id}")

    match = await db.get(Match, match_id)
    if match is None:
        raise ValueError(f"Match {match_id} not found")

    session_result = await db.execute(
        select(GameSession).where(GameSession.match_id == match_id)
    )
    session = session_result.scalar_one_or_none()
    if session is None:
        raise ValueError(f"No GameSession for match {match_id}")

    actor_role = _player_role_to_actor_role(player_role)
    if actor_role not in {ActorRole.PROSECUTION, ActorRole.DEFENSE}:
        raise ValueError("Only prosecution and defense attorneys can raise objections.")

    is_prosecution_player = actor_role == ActorRole.PROSECUTION

    if is_prosecution_player and session.prosecution_objection_used:
        raise ValueError("You have already used your objection this session.")
    if not is_prosecution_player and session.defense_objection_used:
        raise ValueError("You have already used your objection this session.")

    # Find the most recent non-skipped opponent turn
    opponent_role = ActorRole.DEFENSE if is_prosecution_player else ActorRole.PROSECUTION
    target_index = None
    for i in range(len(runtime_state.transcript) - 1, -1, -1):
        t = runtime_state.transcript[i]
        if t.actor_role == opponent_role and not t.skipped:
            target_index = i
            break

    if target_index is None:
        raise ValueError("No opponent argument to object to yet.")

    # Annotate the TurnRecord in memory
    updated_turn = runtime_state.transcript[target_index].model_copy(
        update={"system_note": "[OBJECTION RAISED]"}
    )
    new_transcript = list(runtime_state.transcript)
    new_transcript[target_index] = updated_turn
    runtime_state = runtime_state.model_copy(update={"transcript": new_transcript})
    game_store.save(match_id_str, runtime_state)

    # Mark the corresponding DB Round row
    rounds_result = await db.execute(
        select(Round)
        .where(Round.game_session_id == session.id)
        .order_by(Round.round_number)
    )
    all_rounds = rounds_result.scalars().all()
    if target_index < len(all_rounds):
        all_rounds[target_index].was_objected = True

    # Consume the player's one-time objection token
    if is_prosecution_player:
        session.prosecution_objection_used = True
    else:
        session.defense_objection_used = True

    await db.commit()

    return _build_game_state_response(match, session, runtime_state)


# ── Get game state ────────────────────────────────────────────────────────────

async def advance_one_ai_turn(match_id: uuid.UUID, db: AsyncSession) -> dict[str, Any]:
    """
    Process exactly one AI turn for spectator/judge modes.
    The frontend calls this repeatedly to drive the match turn-by-turn.
    Returns the updated game state after the turn completes.
    If the match is already waiting for human input or is complete, returns
    the current state unchanged.
    """
    match_id_str = str(match_id)
    runtime_state = game_store.get(match_id_str)
    if runtime_state is None:
        raise ValueError(f"No active game session for match {match_id}")

    match = await db.get(Match, match_id)
    if match is None:
        raise ValueError(f"Match {match_id} not found")

    session_result = await db.execute(
        select(GameSession).where(GameSession.match_id == match_id)
    )
    session = session_result.scalar_one_or_none()
    if session is None:
        raise ValueError(f"No GameSession for match {match_id}")

    result = bi_progress_one_turn(state=runtime_state)
    runtime_state = result.state

    await _sync_transcript_to_db(session.id, runtime_state, db)
    await _sync_session_state(session, runtime_state, db)

    if result.action == ProgressAction.MATCH_COMPLETED:
        await _finalize_match(match, runtime_state, db)

    await db.commit()
    game_store.save(match_id_str, runtime_state)

    return _build_game_state_response(match, session, runtime_state)


async def get_game_state(match_id: uuid.UUID, db: AsyncSession) -> dict[str, Any]:
    """Return the current game state for API response."""
    match_id_str = str(match_id)
    runtime_state = game_store.get(match_id_str)

    match = await db.get(Match, match_id)
    if match is None:
        raise ValueError(f"Match {match_id} not found")

    session_result = await db.execute(
        select(GameSession).where(GameSession.match_id == match_id)
    )
    session = session_result.scalar_one_or_none()
    if session is None:
        raise ValueError(f"No GameSession for match {match_id}")

    if runtime_state:
        return _build_game_state_response(match, session, runtime_state)

    # Fallback: return DB-only state (for completed matches without in-memory state)
    return {
        "match_id": match_id_str,
        "status": match.status.value,
        "current_round": session.current_round,
        "max_rounds": session.max_rounds,
        "current_turn": session.current_turn,
        "scales_value": session.scales_value,
        "case_summary": match.case_summary,
        "verdict": match.verdict.value if match.verdict else None,
        "verdict_reasoning": match.verdict_reasoning,
        "transcript": json.loads(session.transcript_json) if session.transcript_json else [],
        "evidence": [],
        "waiting_for": None,
        "objection_available": False,
    }


# ── Get available evidence for the player ─────────────────────────────────────

async def get_player_evidence(
    match_id: uuid.UUID,
    player_role: PlayerRole,
    db: AsyncSession,
) -> list[dict[str, Any]]:
    """Return evidence cards available to the player based on their role."""
    match_id_str = str(match_id)
    runtime_state = game_store.get(match_id_str)

    if runtime_state:
        actor_role = _player_role_to_actor_role(player_role)
        if actor_role is None:
            # Spectators see no evidence
            return []
        cards = get_available_evidence(state=runtime_state, role=actor_role)
        return [card.model_dump() for card in cards]

    # Fallback: query DB
    role_filter = _player_role_to_evidence_role(player_role)
    if role_filter is None:
        return []

    query = select(Evidence).where(
        Evidence.match_id == match_id,
        Evidence.assigned_role.in_(role_filter),
    ).order_by(Evidence.card_order)
    result = await db.execute(query)
    evidence_items = result.scalars().all()
    return [
        {
            "id": str(e.id),
            "code": e.title,  # fallback; runtime uses "code" field
            "title": e.title,
            "description": e.description,
            "assigned_role": e.assigned_role.value,
            "is_used": e.is_used,
            "used_in_round": e.used_in_round,
            "card_order": e.card_order,
        }
        for e in evidence_items
    ]


# ── Internal helpers ──────────────────────────────────────────────────────────

def _player_role_to_evidence_role(player_role: PlayerRole) -> list[EvidenceRole] | None:
    """Map player role to which evidence roles they can see."""
    mapping = {
        PlayerRole.DEFENSE_ATTORNEY: [EvidenceRole.DEFENSE, EvidenceRole.SHARED],
        PlayerRole.PROSECUTOR: [EvidenceRole.PROSECUTION, EvidenceRole.SHARED],
        PlayerRole.JUDGE: [EvidenceRole.DEFENSE, EvidenceRole.PROSECUTION, EvidenceRole.SHARED],
    }
    return mapping.get(player_role)


async def _persist_evidence(
    match_id: uuid.UUID,
    case_file: CaseFileBundle,
    db: AsyncSession,
) -> None:
    """Persist all evidence cards from the case file to the DB."""
    order = 0
    for card in case_file.prosecution_evidence:
        db.add(Evidence(
            match_id=match_id,
            title=card.title,
            description=card.description,
            assigned_role=EvidenceRole.PROSECUTION,
            card_order=order,
        ))
        order += 1

    for card in case_file.defense_evidence:
        db.add(Evidence(
            match_id=match_id,
            title=card.title,
            description=card.description,
            assigned_role=EvidenceRole.DEFENSE,
            card_order=order,
        ))
        order += 1

    for card in case_file.shared_evidence:
        db.add(Evidence(
            match_id=match_id,
            title=card.title,
            description=card.description,
            assigned_role=EvidenceRole.SHARED,
            card_order=order,
        ))
        order += 1


async def _get_evidence_code(
    evidence_id: uuid.UUID,
    match_id: uuid.UUID,
    runtime_state: MatchRuntimeState | None,
    db: AsyncSession,
) -> str | None:
    """
    Map a DB evidence UUID to its runtime evidence code.

    The AI engine generates evidence with codes like 'EVD-DEF-001'.
    When persisting to DB we store the title. To map back, we look up the
    DB evidence title and find the matching runtime EvidenceCard by title.
    """
    evidence = await db.get(Evidence, evidence_id)
    if evidence is None:
        return None

    if runtime_state and runtime_state.case_file:
        # Search all evidence lists for a card with a matching title
        all_cards = (
            runtime_state.case_file.prosecution_evidence
            + runtime_state.case_file.defense_evidence
            + runtime_state.case_file.shared_evidence
        )
        for card in all_cards:
            if card.title == evidence.title:
                return card.code

    # Fallback: use the title itself as the code
    return evidence.title


async def _mark_evidence_used_in_db(evidence_id: uuid.UUID, db: AsyncSession) -> None:
    """Mark an evidence card as used in the database."""
    evidence = await db.get(Evidence, evidence_id)
    if evidence:
        evidence.is_used = True


def _map_speaker(turn: TurnRecord) -> RoundSpeaker:
    """Map backend_integration ActorRole to Round speaker enum."""
    mapping = {
        ActorRole.PROSECUTION: RoundSpeaker.AI_PROSECUTION,
        ActorRole.DEFENSE: RoundSpeaker.AI_DEFENSE,
        ActorRole.JUDGE: RoundSpeaker.AI_JUDGE,
    }
    # Check if the turn was by a human — use PLAYER
    from backend_integration.models.actors import ActorController
    if turn.controller == ActorController.HUMAN:
        return RoundSpeaker.PLAYER
    return mapping.get(turn.actor_role, RoundSpeaker.PLAYER)


async def _sync_transcript_to_db(
    session_id: uuid.UUID,
    runtime_state: MatchRuntimeState,
    db: AsyncSession,
) -> None:
    """
    Sync the runtime transcript to the rounds table.
    Only creates Round rows for turns that don't already exist.
    """
    # Count existing rounds
    result = await db.execute(
        select(Round).where(Round.game_session_id == session_id)
    )
    existing_rounds = result.scalars().all()
    existing_count = len(existing_rounds)

    # Create new rounds for any turns not yet persisted
    for turn in runtime_state.transcript[existing_count:]:
        round_obj = Round(
            game_session_id=session_id,
            round_number=turn.turn_index,
            speaker=_map_speaker(turn),
            argument_text=turn.text,
            was_objected=False,
            scales_delta=None,
        )
        db.add(round_obj)

    # Also persist the full transcript as JSON on the session
    _code_to_title: dict[str, str] = {}
    if runtime_state.case_file:
        for _card in (
            runtime_state.case_file.prosecution_evidence
            + runtime_state.case_file.defense_evidence
            + runtime_state.case_file.shared_evidence
        ):
            _code_to_title[_card.code] = _card.title

    transcript_data = [
        {
            "turn_index": t.turn_index,
            "cycle": t.cycle_number,
            "actor": t.actor_role.value,
            "controller": t.controller.value,
            "text": t.text,
            "evidence_ids": [_code_to_title.get(code, code) for code in t.attached_evidence_ids[:1]],
            "skipped": t.skipped,
        }
        for t in runtime_state.transcript
    ]
    result = await db.execute(
        select(GameSession).where(GameSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    if session:
        session.transcript_json = json.dumps(transcript_data, ensure_ascii=False)


async def _sync_session_state(
    session: GameSession,
    runtime_state: MatchRuntimeState,
    db: AsyncSession,
) -> None:
    """Sync runtime state fields back to the GameSession row."""
    session.current_round = runtime_state.current_cycle
    session.current_turn = runtime_state.next_actor.value if runtime_state.next_actor else None

    # Compute scales_value from verdict scores if available
    if runtime_state.verdict:
        d_score = runtime_state.verdict.defense_score or 5
        p_score = runtime_state.verdict.prosecution_score or 5
        total = d_score + p_score
        if total > 0:
            session.scales_value = round((d_score - p_score) / total, 4)
    elif runtime_state.transcript:
        # Approximate scales from turn count balance
        defense_turns = sum(1 for t in runtime_state.transcript if t.actor_role == ActorRole.DEFENSE and not t.skipped)
        prosecution_turns = sum(1 for t in runtime_state.transcript if t.actor_role == ActorRole.PROSECUTION and not t.skipped)
        total_turns = defense_turns + prosecution_turns
        if total_turns > 0:
            session.scales_value = round((defense_turns - prosecution_turns) / total_turns, 4)


async def _finalize_match(
    match: Match,
    runtime_state: MatchRuntimeState,
    db: AsyncSession,
) -> None:
    """Mark the match as completed and update verdict + user stats."""
    match.status = MatchStatus.COMPLETED
    match.completed_at = datetime.now(timezone.utc)

    if runtime_state.verdict:
        if runtime_state.verdict.guilty is True:
            match.verdict = Verdict.GUILTY
        elif runtime_state.verdict.guilty is False:
            match.verdict = Verdict.NOT_GUILTY
        else:
            match.verdict = Verdict.PENDING

        match.verdict_reasoning = runtime_state.verdict.reasoning
        match.total_rounds = len(runtime_state.transcript)

        # Update user win stats (US3)
        player = await db.get(User, match.player_id)
        if player:
            if match.player_role == PlayerRole.DEFENSE_ATTORNEY and match.verdict == Verdict.NOT_GUILTY:
                player.total_wins += 1
            elif match.player_role == PlayerRole.PROSECUTOR and match.verdict == Verdict.GUILTY:
                player.total_wins += 1
            # Judge and Spectator don't get win/loss tracking


def _build_game_state_response(
    match: Match,
    session: GameSession,
    runtime_state: MatchRuntimeState,
) -> dict[str, Any]:
    """Build a rich game state response dict for the API."""
    # Determine what the frontend should show
    status_map = {
        BiMatchStatus.IN_PROGRESS: "in_progress",
        BiMatchStatus.AWAITING_HUMAN_TURN: "awaiting_human_turn",
        BiMatchStatus.AWAITING_HUMAN_VERDICT: "awaiting_human_verdict",
        BiMatchStatus.COMPLETED: "completed",
        BiMatchStatus.QUIT: "quit",
    }

    code_to_evidence: dict[str, dict[str, str]] = {}
    if runtime_state.case_file:
        for _card in (
            runtime_state.case_file.prosecution_evidence
            + runtime_state.case_file.defense_evidence
            + runtime_state.case_file.shared_evidence
        ):
            code_to_evidence[_card.code] = {"title": _card.title, "desc": _card.description}

    transcript = [
        {
            "turn_index": t.turn_index,
            "cycle": t.cycle_number,
            "actor": t.actor_role.value,
            "controller": t.controller.value,
            "text": t.text,
            "evidence_ids": [code_to_evidence.get(code, {}).get("title", code) for code in t.attached_evidence_ids[:1]],
            "evidence_used": [
                code_to_evidence[code]
                for code in t.attached_evidence_ids[:1]
                if code in code_to_evidence
            ],
            "skipped": t.skipped,
            "system_note": t.system_note,
        }
        for t in runtime_state.transcript
    ]

    verdict_data = None
    if runtime_state.verdict:
        verdict_data = {
            "guilty": runtime_state.verdict.guilty,
            "reasoning": runtime_state.verdict.reasoning,
            "prosecution_score": runtime_state.verdict.prosecution_score,
            "defense_score": runtime_state.verdict.defense_score,
            "verdict_text": runtime_state.verdict.verdict_text,
        }

    case_summary = None
    if runtime_state.case_file and runtime_state.case_file.summary:
        case_summary = {
            "crime": runtime_state.case_file.summary.crime,
            "charges": runtime_state.case_file.summary.charges,
            "background_story": runtime_state.case_file.summary.background_story,
        }

    objection_available = (
        match.player_role == PlayerRole.PROSECUTOR and not session.prosecution_objection_used
        or match.player_role == PlayerRole.DEFENSE_ATTORNEY and not session.defense_objection_used
    )

    return {
        "match_id": str(match.id),
        "session_id": str(session.id),
        "status": status_map.get(runtime_state.status, runtime_state.status.value),
        "player_role": match.player_role.value,
        "current_round": runtime_state.current_cycle,
        "max_rounds": runtime_state.config.max_rounds,
        "current_turn": runtime_state.next_actor.value if runtime_state.next_actor else None,
        "scales_value": session.scales_value,
        "case_summary": case_summary,
        "transcript": transcript,
        "verdict": verdict_data,
        "waiting_for": (
            runtime_state.next_actor.value
            if runtime_state.status in {BiMatchStatus.AWAITING_HUMAN_TURN, BiMatchStatus.AWAITING_HUMAN_VERDICT}
            else None
        ),
        "system_events": runtime_state.system_events,
        "objection_available": objection_available,
    }
