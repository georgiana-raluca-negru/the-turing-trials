from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from backend_integration.models.actors import ActorController, ActorRole


class HumanTurnInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    actor_role: ActorRole
    text: str = Field(..., min_length=1)
    attached_evidence_ids: list[str] = Field(default_factory=list)


class HumanJudgeVerdictInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    guilty: bool
    reasoning: str = Field(..., min_length=1)
    prosecution_score: int | None = Field(default=None, ge=1, le=10)
    defense_score: int | None = Field(default=None, ge=1, le=10)


class TurnRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    turn_index: int
    cycle_number: int
    actor_role: ActorRole
    controller: ActorController
    text: str = Field(..., min_length=1)
    attached_evidence_ids: list[str] = Field(default_factory=list)
    skipped: bool = False
    system_note: str | None = None


class VerdictRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    guilty: bool | None = None
    reasoning: str = ""
    prosecution_score: int | None = Field(default=None, ge=1, le=10)
    defense_score: int | None = Field(default=None, ge=1, le=10)
    verdict_text: str = Field(..., min_length=1)
