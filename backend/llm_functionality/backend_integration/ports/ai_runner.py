from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from backend_integration.models.actors import ActorRole
from backend_integration.models.case_file import CaseFileBundle
from backend_integration.models.match import MatchRuntimeState
from backend_integration.models.turns import TurnRecord, VerdictRecord


@dataclass
class AIRunnerTurnResult:
    turn: TurnRecord
    updated_case_file: CaseFileBundle
    system_events: list[str]


@dataclass
class AIRunnerJudgeResult:
    turn: TurnRecord
    verdict: VerdictRecord
    system_events: list[str]


class AIRunnerPort(Protocol):
    def generate_case(self, *, user_prompt: str, allow_evidence_reuse: bool) -> CaseFileBundle:
        ...

    def run_actor_turn(self, *, state: MatchRuntimeState, actor_role: ActorRole) -> AIRunnerTurnResult:
        ...

    def run_judge_turn(self, *, state: MatchRuntimeState) -> AIRunnerJudgeResult:
        ...
