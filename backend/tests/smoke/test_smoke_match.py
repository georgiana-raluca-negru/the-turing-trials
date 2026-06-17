from __future__ import annotations

import httpx
import pytest

pytestmark = [pytest.mark.asyncio, pytest.mark.smoke]

MATCH_PAYLOAD = {
    "player_prompt": "A museum theft with disputed forensic evidence and conflicting witness stories.",
    "player_role": "defense_attorney",
    "max_rounds": 3,
}

async def _create_match(async_client: httpx.AsyncClient) -> dict:
    response = await async_client.post("/api/matches/", json=MATCH_PAYLOAD)
    assert response.status_code == 201, response.text
    return response.json()

async def _start_session(async_client: httpx.AsyncClient, match_id: str) -> dict:
    response = await async_client.post(
        "/api/sessions/",
        json={"match_id": match_id, "max_rounds": MATCH_PAYLOAD["max_rounds"]},
    )
    assert response.status_code == 201, response.text
    return response.json()

async def test_match_session_evidence_and_turn_smoke(async_client: httpx.AsyncClient):
    match = await _create_match(async_client)
    assert match["player_prompt"] == MATCH_PAYLOAD["player_prompt"]
    assert match["player_role"] == MATCH_PAYLOAD["player_role"]
    assert match["status"] == "lobby"
    assert match["total_rounds"] == MATCH_PAYLOAD["max_rounds"]

    session = await _start_session(async_client, match["id"])
    assert session["match_id"] == match["id"]
    assert session["player_role"] == MATCH_PAYLOAD["player_role"]
    assert session["status"] in {"awaiting_human_turn", "in_progress"}
    assert isinstance(session["transcript"], list)
    assert isinstance(session["case_summary"], dict)

    evidence_response = await async_client.get(f"/api/evidence/{match['id']}")
    assert evidence_response.status_code == 200, evidence_response.text
    evidence_cards = evidence_response.json()
    assert len(evidence_cards) == 5
    assert {card["assigned_role"] for card in evidence_cards} <= {"defense", "shared"}

    turn_response = await async_client.post(
        f"/api/sessions/{match['id']}/turn",
        json={
            "argument_text": "The badge clone report creates reasonable doubt about who accessed the alarm controls.",
            "attached_evidence_id": evidence_cards[0]["id"],
        },
    )
    assert turn_response.status_code == 200, turn_response.text

    updated_session = turn_response.json()
    assert len(updated_session["transcript"]) > len(session["transcript"])
    assert any(turn["controller"] == "human" for turn in updated_session["transcript"])
