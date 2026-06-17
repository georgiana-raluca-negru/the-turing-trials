from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from backend_integration.interface import (
    create_match,
    get_available_evidence,
    progress_match,
    progress_until_human_or_terminal,
    submit_human_turn,
)
from backend_integration.models.actors import ActorConfiguration, ActorController, ActorRole
from backend_integration.models.case_file import CaseFileBundle, EvidenceCard
from backend_integration.models.match import MatchConfig, MatchStatus, ProgressAction
from backend_integration.models.turns import HumanTurnInput, TurnRecord, VerdictRecord
from backend_integration.ports.ai_runner import AIRunnerJudgeResult, AIRunnerPort, AIRunnerTurnResult
from backend_integration.services.lifecycle import _mark_evidence_used_for_human_turn
from tests.factories import build_case_file_bundle, build_verdict_record
from tests.fakes import ScriptedAIRunner

pytestmark = pytest.mark.agent_eval


@dataclass
class PlannedActorTurn:
    actor_role: ActorRole
    text: str
    attached_evidence_ids: list[str] = field(default_factory=list)
    system_events: list[str] = field(default_factory=list)


@dataclass
class DeterministicAIRunner(AIRunnerPort):
    case_file: CaseFileBundle = field(default_factory=build_case_file_bundle)
    turn_plans: list[PlannedActorTurn] = field(default_factory=list)
    judge_verdict: VerdictRecord = field(default_factory=build_verdict_record)
    judge_system_events: list[str] = field(default_factory=list)

    def generate_case(self, *, user_prompt: str, allow_evidence_reuse: bool) -> CaseFileBundle:
        return self.case_file.model_copy(deep=True)

    def run_actor_turn(self, *, state, actor_role: ActorRole) -> AIRunnerTurnResult:
        if not self.turn_plans:
            raise AssertionError(f"No planned AI turn remained for {actor_role.value}.")

        plan = self.turn_plans.pop(0)
        if plan.actor_role != actor_role:
            raise AssertionError(
                f"Expected planned turn for {plan.actor_role.value}, got {actor_role.value}."
            )

        turn = TurnRecord(
            turn_index=len(state.transcript) + 1,
            cycle_number=state.current_cycle,
            actor_role=actor_role,
            controller=ActorController.AI,
            text=plan.text,
            attached_evidence_ids=list(plan.attached_evidence_ids),
        )
        updated_case_file = _mark_evidence_used_for_human_turn(
            case_file=state.case_file,
            actor_role=actor_role,
            evidence_ids=list(plan.attached_evidence_ids),
            turn_index=turn.turn_index,
        )
        return AIRunnerTurnResult(
            turn=turn,
            updated_case_file=updated_case_file,
            system_events=list(plan.system_events),
        )

    def run_judge_turn(self, *, state) -> AIRunnerJudgeResult:
        verdict = self.judge_verdict.model_copy(deep=True)
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
            system_events=list(self.judge_system_events),
        )


def _build_config(*, max_rounds: int = 2, allow_evidence_reuse: bool = False) -> MatchConfig:
    return MatchConfig(
        user_prompt="A deterministic evidence-behavior evaluation.",
        max_rounds=max_rounds,
        allow_evidence_reuse=allow_evidence_reuse,
    )


def _cards_by_code(cards: list[EvidenceCard]) -> dict[str, EvidenceCard]:
    return {card.code: card for card in cards}


def test_ai_turn_truncates_multiple_requested_evidence_to_one() -> None:
    runner = DeterministicAIRunner(
        case_file=build_case_file_bundle(),
        turn_plans=[
            PlannedActorTurn(
                actor_role=ActorRole.PROSECUTION,
                text="The prosecution over-requests evidence.",
                attached_evidence_ids=["EVD-PRO-002", "EVD-PRO-001"],
            )
        ],
    )
    state = create_match(
        config=_build_config(max_rounds=1, allow_evidence_reuse=False),
        actors=ActorConfiguration(),
        case_file=build_case_file_bundle(),
        ai_runner=runner,
    )

    result = progress_match(state=state, ai_runner=runner)

    assert result.action == ProgressAction.AI_TURN_COMPLETED
    assert result.latest_turn is not None
    assert result.latest_turn.attached_evidence_ids == ["EVD-PRO-002"]

    prosecution_cards = _cards_by_code(result.state.case_file.prosecution_evidence)
    assert prosecution_cards["EVD-PRO-002"].is_used is True
    assert prosecution_cards["EVD-PRO-002"].used_in_turn_index == 1
    assert prosecution_cards["EVD-PRO-001"].is_used is False


def test_human_turn_rejects_multiple_attached_evidence_ids() -> None:
    state = create_match(
        config=_build_config(max_rounds=1, allow_evidence_reuse=False),
        actors=ActorConfiguration(
            prosecution=ActorController.HUMAN,
            defense=ActorController.AI,
            judge=ActorController.AI,
        ),
        case_file=build_case_file_bundle(),
    )

    assert state.status == MatchStatus.AWAITING_HUMAN_TURN
    with pytest.raises(ValueError, match="At most 1 evidence item may be attached to a turn."):
        submit_human_turn(
            state=state,
            human_turn=HumanTurnInput(
                actor_role=ActorRole.PROSECUTION,
                text="The user tries to cite two exhibits at once.",
                attached_evidence_ids=["EVD-PRO-001", "EVD-PRO-002"],
            ),
        )


@pytest.mark.parametrize(
    ("allow_evidence_reuse", "expected_second_attachment", "expected_available_codes", "expected_used_turn"),
    [
        pytest.param(False, [], ["EVD-PRO-002", "EVD-PRO-003", "EVD-PRO-004"], 1, id="no_reuse"),
        pytest.param(True, ["EVD-PRO-001"], ["EVD-PRO-001", "EVD-PRO-002", "EVD-PRO-003", "EVD-PRO-004"], 3, id="reuse_enabled"),
    ],
)
def test_evidence_reuse_toggle_changes_repeated_ai_attachment(
    allow_evidence_reuse: bool,
    expected_second_attachment: list[str],
    expected_available_codes: list[str],
    expected_used_turn: int,
) -> None:
    runner = DeterministicAIRunner(
        case_file=build_case_file_bundle(),
        turn_plans=[
            PlannedActorTurn(
                actor_role=ActorRole.PROSECUTION,
                text="Opening claim.",
                attached_evidence_ids=["EVD-PRO-001"],
            ),
            PlannedActorTurn(
                actor_role=ActorRole.DEFENSE,
                text="Defense response.",
                attached_evidence_ids=["EVD-DEF-001"],
            ),
            PlannedActorTurn(
                actor_role=ActorRole.PROSECUTION,
                text="The prosecution tries to reuse the same exhibit.",
                attached_evidence_ids=["EVD-PRO-001"],
            ),
        ],
    )
    state = create_match(
        config=_build_config(max_rounds=2, allow_evidence_reuse=allow_evidence_reuse),
        actors=ActorConfiguration(),
        case_file=build_case_file_bundle(),
        ai_runner=runner,
    )

    first_result = progress_match(state=state, ai_runner=runner)
    second_result = progress_match(state=first_result.state, ai_runner=runner)
    third_result = progress_match(state=second_result.state, ai_runner=runner)

    assert first_result.latest_turn is not None
    assert first_result.latest_turn.attached_evidence_ids == ["EVD-PRO-001"]
    assert third_result.latest_turn is not None
    assert third_result.latest_turn.attached_evidence_ids == expected_second_attachment

    available_codes = [
        card.code for card in get_available_evidence(state=third_result.state, role=ActorRole.PROSECUTION)
    ]
    assert available_codes == expected_available_codes

    prosecution_cards = _cards_by_code(third_result.state.case_file.prosecution_evidence)
    assert prosecution_cards["EVD-PRO-001"].used_in_turn_index == expected_used_turn


def test_full_ai_match_preserves_turn_order_cycles_and_single_evidence_usage(
    fake_ai_runner: ScriptedAIRunner,
) -> None:
    state = create_match(
        config=_build_config(max_rounds=2, allow_evidence_reuse=False),
        actors=ActorConfiguration(),
        case_file=build_case_file_bundle(),
        ai_runner=fake_ai_runner,
    )

    result = progress_until_human_or_terminal(state=state, ai_runner=fake_ai_runner)

    assert result.action == ProgressAction.MATCH_COMPLETED
    assert result.state.status == MatchStatus.COMPLETED
    assert result.state.verdict is not None

    transcript = result.state.transcript
    assert [turn.turn_index for turn in transcript] == [1, 2, 3, 4, 5]
    assert [turn.actor_role for turn in transcript] == [
        ActorRole.PROSECUTION,
        ActorRole.DEFENSE,
        ActorRole.PROSECUTION,
        ActorRole.DEFENSE,
        ActorRole.JUDGE,
    ]
    assert [turn.cycle_number for turn in transcript] == [1, 1, 2, 2, 2]
    assert [turn.attached_evidence_ids for turn in transcript[:-1]] == [
        ["EVD-PRO-001"],
        ["EVD-DEF-001"],
        ["EVD-PRO-002"],
        ["EVD-DEF-002"],
    ]
    assert transcript[-1].attached_evidence_ids == []

    prosecution_cards = _cards_by_code(result.state.case_file.prosecution_evidence)
    defense_cards = _cards_by_code(result.state.case_file.defense_evidence)
    assert prosecution_cards["EVD-PRO-001"].used_in_turn_index == 1
    assert prosecution_cards["EVD-PRO-002"].used_in_turn_index == 3
    assert defense_cards["EVD-DEF-001"].used_in_turn_index == 2
    assert defense_cards["EVD-DEF-002"].used_in_turn_index == 4
