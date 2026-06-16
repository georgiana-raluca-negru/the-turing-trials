from __future__ import annotations

from dataclasses import dataclass, field

from backend_integration.models.actors import ActorController, ActorRole
from backend_integration.models.case_file import CaseFileBundle
from backend_integration.models.turns import TurnRecord
from backend_integration.ports.ai_runner import AIRunnerJudgeResult, AIRunnerPort, AIRunnerTurnResult
from backend_integration.services.lifecycle import _mark_evidence_used_for_human_turn, get_available_evidence_for_role
from tests.factories import build_case_file_bundle, build_verdict_record


@dataclass
class ScriptedAIRunner(AIRunnerPort):
    case_file: CaseFileBundle = field(default_factory=build_case_file_bundle)
    system_events: list[str] = field(default_factory=list)

    def generate_case(self, *, user_prompt: str, allow_evidence_reuse: bool) -> CaseFileBundle:
        return self.case_file.model_copy(deep=True)

    def run_actor_turn(self, *, state, actor_role: ActorRole) -> AIRunnerTurnResult:
        available = get_available_evidence_for_role(state, actor_role)
        attached_ids = [available[0].code] if available else []
        title = available[0].title if available else "debate history"

        turn = TurnRecord(
            turn_index=len(state.transcript) + 1,
            cycle_number=state.current_cycle,
            actor_role=actor_role,
            controller=ActorController.AI,
            text=f"{actor_role.value.capitalize()} argues from {title}.",
            attached_evidence_ids=attached_ids,
        )

        updated_case_file = _mark_evidence_used_for_human_turn(
            case_file=state.case_file,
            actor_role=actor_role,
            evidence_ids=attached_ids,
            turn_index=turn.turn_index,
        ) if attached_ids else state.case_file.model_copy(deep=True)

        return AIRunnerTurnResult(
            turn=turn,
            updated_case_file=updated_case_file,
            system_events=list(self.system_events),
        )

    def run_judge_turn(self, *, state) -> AIRunnerJudgeResult:
        verdict = build_verdict_record(guilty=False)
        turn = TurnRecord(
            turn_index=len(state.transcript) + 1,
            cycle_number=state.current_cycle,
            actor_role=ActorRole.JUDGE,
            controller=ActorController.AI,
            text=verdict.verdict_text,
            attached_evidence_ids=[],
        )
        return AIRunnerJudgeResult(
            turn=turn,
            verdict=verdict,
            system_events=list(self.system_events),
        )
