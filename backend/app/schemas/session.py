# backend/app/schemas/session.py
"""
Schemas for game session, rounds, objections, and verdict (US9–US13).
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.round import RoundSpeaker


# ── Session ───────────────────────────────────────────────────────────────────

class SessionCreate(BaseModel):
    """Start a new game session for an existing match."""
    match_id: uuid.UUID
    max_rounds: int = Field(default=5, ge=3, le=10)


class ScalesOut(BaseModel):
    """US12 — current Scales of Justice state."""
    session_id: uuid.UUID
    scales_value: float          # -1.0 (prosecution) → +1.0 (defense)
    current_round: int
    max_rounds: int
    current_turn: str | None


class SessionOut(BaseModel):
    """Full session state."""
    id: uuid.UUID
    match_id: uuid.UUID
    current_round: int
    max_rounds: int
    current_turn: str | None
    scales_value: float
    started_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Rounds (US9) ──────────────────────────────────────────────────────────────

class RoundCreate(BaseModel):
    """
    US9 — A player submits their argument for this round.
    *attached_evidence_id* is required for human players; AI rounds supply None.
    """
    argument_text: str = Field(..., min_length=10, max_length=5000)
    attached_evidence_id: uuid.UUID | None = None


class RoundOut(BaseModel):
    """A single round record."""
    id: uuid.UUID
    round_number: int
    speaker: RoundSpeaker
    argument_text: str
    attached_evidence_id: uuid.UUID | None
    was_objected: bool
    objection_text: str | None
    objection_response: str | None
    scales_delta: float | None
    judge_feedback: str | None
    submitted_at: datetime

    model_config = {"from_attributes": True}


# ── Objection (US11) ──────────────────────────────────────────────────────────

class ObjectionCreate(BaseModel):
    """
    US11 — The player triggers an Objection during the opponent's turn.
    The *round_id* identifies which in-progress round to interrupt.
    """
    round_id: uuid.UUID
    objection_text: str = Field(..., min_length=5, max_length=1000)


class ObjectionResponse(BaseModel):
    round_id: uuid.UUID
    objection_accepted: bool
    objection_response: str    # AI-generated rebuttal or sustain reasoning


# ── Verdict (US13) ────────────────────────────────────────────────────────────

class VerdictCreate(BaseModel):
    """
    US13 — The Judge (human or AI) submits the final verdict.
    verdict must be 'guilty' or 'not_guilty'.
    """
    verdict: str = Field(..., pattern="^(guilty|not_guilty)$")
    verdict_reasoning: str = Field(..., min_length=20, max_length=5000)


class VerdictOut(BaseModel):
    match_id: uuid.UUID
    verdict: str
    verdict_reasoning: str
    scales_final: float
    completed_at: datetime

    model_config = {"from_attributes": True}

