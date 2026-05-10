# backend/app/schemas/match.py
"""
Schemas for match creation and retrieval (US4, US5, US7, US13).
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.match import PlayerRole, MatchStatus, Verdict


# ── Creation ──────────────────────────────────────────────────────────────────

class MatchCreate(BaseModel):
    """US4 + US5 — prompt from player and their chosen role."""
    player_prompt: str = Field(..., min_length=10, max_length=1000)
    player_role: PlayerRole
    max_rounds: int = Field(default=5, ge=3, le=10)


# ── Responses ─────────────────────────────────────────────────────────────────

class MatchOut(BaseModel):
    """Full match detail (US7)."""
    id: uuid.UUID
    player_id: uuid.UUID
    player_prompt: str
    case_summary: str | None
    case_file_json: str | None      # raw JSON string from AI Clerk
    player_role: PlayerRole
    status: MatchStatus
    total_rounds: int
    verdict: Verdict
    verdict_reasoning: str | None
    created_at: datetime
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class MatchListOut(BaseModel):
    """Compact match item for list endpoints."""
    id: uuid.UUID
    player_role: PlayerRole
    case_summary: str | None
    verdict: Verdict
    status: MatchStatus
    created_at: datetime

    model_config = {"from_attributes": True}
