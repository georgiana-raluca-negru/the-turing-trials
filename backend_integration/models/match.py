from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from backend_integration.models.actors import ActorConfiguration, ActorRole
from backend_integration.models.case_file import CaseFileBundle
from backend_integration.models.turns import TurnRecord, VerdictRecord


class MatchStatus(str, Enum):
    IN_PROGRESS = "in_progress"
    AWAITING_HUMAN_TURN = "awaiting_human_turn"
    AWAITING_HUMAN_VERDICT = "awaiting_human_verdict"
    COMPLETED = "completed"
    QUIT = "quit"


class ProgressAction(str, Enum):
    AI_TURN_COMPLETED = "ai_turn_completed"
    HUMAN_TURN_COMPLETED = "human_turn_completed"
    AWAITING_HUMAN_TURN = "awaiting_human_turn"
    AWAITING_HUMAN_VERDICT = "awaiting_human_verdict"
    MATCH_COMPLETED = "match_completed"
    MATCH_QUIT = "match_quit"
    NO_OP = "no_op"


class MatchConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    match_id: str | None = None
    user_prompt: str = Field(..., min_length=1)
    max_rounds: int = Field(default=3, ge=1)
    allow_evidence_reuse: bool = False


class MatchRuntimeState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    config: MatchConfig
    actors: ActorConfiguration
    case_file: CaseFileBundle
    status: MatchStatus = MatchStatus.IN_PROGRESS
    current_cycle: int = Field(default=1, ge=1)
    next_actor: ActorRole = ActorRole.PROSECUTION
    transcript: list[TurnRecord] = Field(default_factory=list)
    system_events: list[str] = Field(default_factory=list)
    verdict: VerdictRecord | None = None
    quit_reason: str | None = None
    quit_actor: ActorRole | None = None

    @model_validator(mode="after")
    def validate_state(self) -> "MatchRuntimeState":
        if self.status == MatchStatus.QUIT and not self.quit_reason:
            raise ValueError("quit_reason is required when status is quit")
        if self.status == MatchStatus.COMPLETED and self.verdict is None:
            raise ValueError("verdict is required when status is completed")
        return self


class MatchProgressResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    state: MatchRuntimeState
    action: ProgressAction
    latest_turn: TurnRecord | None = None
    waiting_for_actor: ActorRole | None = None
    message: str = ""
