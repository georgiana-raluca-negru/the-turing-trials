from __future__ import annotations

import json
import uuid

import httpx
import pytest
from sqlalchemy import select

from app.models.evidence import Evidence, EvidenceRole
from app.models.game_session import GameSession
from app.models.match import Match, MatchStatus
from app.models.round import Round, RoundSpeaker
from app.models.user import User

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


MATCH_PROMPT = (
    "A museum theft with disputed forensic evidence and conflicting witness stories."
)
DEFENSE_ARGUMENT = (
    "The badge clone report creates reasonable doubt because someone else could "
    "have triggered the alarm suppression window."
)


def _as_uuid(value: str | uuid.UUID) -> uuid.UUID:
    if isinstance(value, uuid.UUID):
        return value
    return uuid.UUID(value)


async def _create_match(
    client: httpx.AsyncClient,
    *,
    player_role: str,
    max_rounds: int = 3,
) -> dict:
    response = await client.post(
        "/api/matches/",
        json={
            "player_prompt": MATCH_PROMPT,
            "player_role": player_role,
            "max_rounds": max_rounds,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _start_session(
    client: httpx.AsyncClient,
    match_id: str,
    *,
    max_rounds: int = 3,
) -> dict:
    response = await client.post(
        "/api/sessions/",
        json={"match_id": match_id, "max_rounds": max_rounds},
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _list_evidence(client: httpx.AsyncClient, match_id: str) -> list[dict]:
    response = await client.get(f"/api/evidence/{match_id}")
    assert response.status_code == 200, response.text
    return response.json()


async def _get_transcript(client: httpx.AsyncClient, match_id: str) -> list[dict]:
    response = await client.get(f"/api/sessions/{match_id}/transcript")
    assert response.status_code == 200, response.text
    return response.json()


async def _get_match_row(db_session, match_id: str | uuid.UUID) -> Match:
    match = await db_session.get(Match, _as_uuid(match_id), populate_existing=True)
    assert match is not None
    return match


async def _get_user_row(db_session, user_id: uuid.UUID) -> User:
    user = await db_session.get(User, user_id, populate_existing=True)
    assert user is not None
    return user


async def _get_session_row(db_session, match_id: str | uuid.UUID) -> GameSession:
    result = await db_session.execute(
        select(GameSession)
        .where(GameSession.match_id == _as_uuid(match_id))
        .execution_options(populate_existing=True)
    )
    session = result.scalar_one_or_none()
    assert session is not None
    return session


async def _get_round_rows(db_session, session_id: uuid.UUID) -> list[Round]:
    result = await db_session.execute(
        select(Round)
        .where(Round.game_session_id == session_id)
        .order_by(Round.round_number)
        .execution_options(populate_existing=True)
    )
    return list(result.scalars().all())


async def _get_evidence_rows(db_session, match_id: str | uuid.UUID) -> list[Evidence]:
    result = await db_session.execute(
        select(Evidence)
        .where(Evidence.match_id == _as_uuid(match_id))
        .order_by(Evidence.card_order)
        .execution_options(populate_existing=True)
    )
    return list(result.scalars().all())


async def test_starting_defense_session_persists_match_session_and_evidence(
    async_client: httpx.AsyncClient,
    db_session,
    persisted_user: User,
):
    match = await _create_match(async_client, player_role="defense_attorney")
    created_match = await _get_match_row(db_session, match["id"])
    assert created_match.status == MatchStatus.LOBBY
    assert created_match.case_file_json is None

    session = await _start_session(async_client, match["id"])
    session_snapshot = await async_client.get(f"/api/sessions/{match['id']}")
    assert session_snapshot.status_code == 200, session_snapshot.text
    match_detail = await async_client.get(f"/api/matches/{match['id']}")
    assert match_detail.status_code == 200, match_detail.text

    match_row = await _get_match_row(db_session, match["id"])
    user_row = await _get_user_row(db_session, persisted_user.id)
    session_row = await _get_session_row(db_session, match["id"])
    round_rows = await _get_round_rows(db_session, session_row.id)
    evidence_rows = await _get_evidence_rows(db_session, match["id"])

    assert session["match_id"] == match["id"]
    assert session["player_role"] == "defense_attorney"
    assert session["status"] == "awaiting_human_turn"
    assert session["waiting_for"] == "defense"
    assert session["current_round"] == 1
    assert session["current_turn"] == "defense"
    assert session["scales_value"] == -1.0
    assert len(session["transcript"]) == 1
    assert session["transcript"][0]["actor"] == "prosecution"
    assert session["transcript"][0]["controller"] == "ai"
    assert session["transcript"][0]["evidence_ids"] == ["Surveillance Footage"]
    assert session["transcript"][0]["text"] == "Prosecution argues from Surveillance Footage."
    assert session_snapshot.json()["transcript"] == session["transcript"]

    assert match_detail.json()["status"] == "in_progress"
    assert match_detail.json()["case_file_json"] is not None

    assert match_row.status == MatchStatus.IN_PROGRESS
    assert match_row.case_summary == "Museum Theft: Grand Larceny, Destruction of Property"
    assert match_row.case_file_json is not None
    assert json.loads(match_row.case_file_json)["summary"]["crime"] == "Museum Theft"
    assert user_row.total_matches == 1
    assert user_row.total_wins == 0

    assert session_row.current_round == 1
    assert session_row.max_rounds == 3
    assert session_row.current_turn == "defense"
    assert session_row.scales_value == -1.0
    assert session_row.transcript_json is not None
    assert json.loads(session_row.transcript_json)[0]["evidence_ids"] == ["Surveillance Footage"]

    assert len(round_rows) == 1
    assert round_rows[0].round_number == 1
    assert round_rows[0].speaker == RoundSpeaker.AI_PROSECUTION
    assert round_rows[0].argument_text == "Prosecution argues from Surveillance Footage."

    assert len(evidence_rows) == 9
    assert {row.assigned_role for row in evidence_rows} == {
        EvidenceRole.PROSECUTION,
        EvidenceRole.DEFENSE,
        EvidenceRole.SHARED,
    }


async def test_submitting_defense_turn_updates_transcript_and_marks_evidence_used(
    async_client: httpx.AsyncClient,
    db_session,
):
    match = await _create_match(async_client, player_role="defense_attorney")
    await _start_session(async_client, match["id"])
    evidence_cards = await _list_evidence(async_client, match["id"])
    selected_evidence = next(card for card in evidence_cards if card["assigned_role"] == "defense")

    response = await async_client.post(
        f"/api/sessions/{match['id']}/turn",
        json={
            "argument_text": DEFENSE_ARGUMENT,
            "attached_evidence_id": selected_evidence["id"],
        },
    )
    assert response.status_code == 200, response.text
    state = response.json()

    session_row = await _get_session_row(db_session, match["id"])
    round_rows = await _get_round_rows(db_session, session_row.id)
    transcript_rows = await _get_transcript(async_client, match["id"])
    selected_evidence_row = await db_session.get(Evidence, _as_uuid(selected_evidence["id"]))
    assert selected_evidence_row is not None

    assert state["status"] == "awaiting_human_turn"
    assert state["waiting_for"] == "defense"
    assert state["current_round"] == 2
    assert state["current_turn"] == "defense"
    assert [turn["actor"] for turn in state["transcript"]] == [
        "prosecution",
        "defense",
        "prosecution",
    ]
    assert state["transcript"][1]["controller"] == "human"
    assert state["transcript"][1]["text"] == DEFENSE_ARGUMENT
    assert state["transcript"][1]["evidence_ids"] == [selected_evidence["title"]]
    assert state["transcript"][2]["text"] == "Prosecution argues from Glass Fragments."

    assert len(round_rows) == 3
    assert [row.speaker for row in round_rows] == [
        RoundSpeaker.AI_PROSECUTION,
        RoundSpeaker.PLAYER,
        RoundSpeaker.AI_PROSECUTION,
    ]
    assert round_rows[1].argument_text == DEFENSE_ARGUMENT

    assert len(transcript_rows) == 3
    assert transcript_rows[1]["speaker"] == "player"
    assert transcript_rows[1]["argument_text"] == DEFENSE_ARGUMENT

    assert selected_evidence_row.is_used is True
    assert session_row.transcript_json is not None
    persisted_transcript = json.loads(session_row.transcript_json)
    assert persisted_transcript[1]["controller"] == "human"
    assert persisted_transcript[1]["evidence_ids"] == [selected_evidence["title"]]


async def test_defense_objection_marks_latest_opponent_round_and_consumes_token(
    async_client: httpx.AsyncClient,
    db_session,
):
    match = await _create_match(async_client, player_role="defense_attorney")
    await _start_session(async_client, match["id"])

    response = await async_client.post(f"/api/sessions/{match['id']}/objection")
    assert response.status_code == 200, response.text
    state = response.json()

    session_row = await _get_session_row(db_session, match["id"])
    round_rows = await _get_round_rows(db_session, session_row.id)
    transcript_rows = await _get_transcript(async_client, match["id"])

    assert state["objection_available"] is False
    assert state["transcript"][0]["system_note"] == "[OBJECTION RAISED]"
    assert session_row.defense_objection_used is True
    assert session_row.prosecution_objection_used is False
    assert round_rows[0].was_objected is True
    assert transcript_rows[0]["was_objected"] is True

    second_response = await async_client.post(f"/api/sessions/{match['id']}/objection")
    assert second_response.status_code == 400
    assert second_response.json()["detail"] == "You have already used your objection this session."
