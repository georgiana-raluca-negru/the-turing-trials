"""Integration tests for backend_integration's match lifecycle wiring.

These exercise create_match_state/progress_match_state/quit_match_state together,
through a fake AIRunnerPort implementation -- no real LLM, no LangGraph, no network.
The goal is to catch breakage in how the pieces are wired (state transitions, turn
ordering, evidence-availability enforcement) rather than any single function's logic,
which the unit tests already cover.
"""

import pytest

from backend_integration.models.actors import ActorConfiguration, ActorController, ActorRole
from backend_integration.models.case_file import CaseFileBundle, CaseSummary, EvidenceCard, EvidenceRole
from backend_integration.models.match import MatchConfig, MatchStatus, ProgressAction
from backend_integration.models.turns import HumanTurnInput, TurnRecord, VerdictRecord
from backend_integration.ports.ai_runner import AIRunnerJudgeResult, AIRunnerTurnResult
from backend_integration.services.lifecycle import (
    create_match_state,
    get_available_evidence_for_role,
    get_match_snapshot_state,
    progress_match_state,
    progress_until_pause_or_completion,
    quit_match_state,
)

pytestmark = pytest.mark.integration


class FakeAIRunner:
    """A hand-written AIRunnerPort, standing in for AIEngineAdapter + the real LLM."""

    def __init__(self, *, attach_evidence: bool = True, attached_ids_override: list[str] | None = None):
        self.attach_evidence = attach_evidence
        self.attached_ids_override = attached_ids_override
        self.run_actor_turn_calls: list[ActorRole] = []
        self.run_judge_turn_calls = 0

    def generate_case(self, *, user_prompt, allow_evidence_reuse):
        raise AssertionError("generate_case should not be called when a case_file is supplied directly")

    def run_actor_turn(self, *, state, actor_role):
        self.run_actor_turn_calls.append(actor_role)
        available = get_available_evidence_for_role(state, actor_role)

        if self.attached_ids_override is not None:
            attached_ids = list(self.attached_ids_override)
        elif self.attach_evidence and available:
            attached_ids = [available[0].code]
        else:
            attached_ids = []

        turn = TurnRecord(
            turn_index=len(state.transcript) + 1,
            cycle_number=state.current_cycle,
            actor_role=actor_role,
            controller=ActorController.AI,
            text=f"{actor_role.value} argument for turn {len(state.transcript) + 1}.",
            attached_evidence_ids=attached_ids,
        )

        updated_case_file = state.case_file.model_copy(deep=True)
        if attached_ids:
            list_name = "prosecution_evidence" if actor_role == ActorRole.PROSECUTION else "defense_evidence"
            selected = set(attached_ids)
            evidence_list = getattr(updated_case_file, list_name)
            setattr(
                updated_case_file,
                list_name,
                [
                    item.model_copy(update={"is_used": True}) if item.code in selected else item
                    for item in evidence_list
                ],
            )

        return AIRunnerTurnResult(turn=turn, updated_case_file=updated_case_file, system_events=[])

    def run_judge_turn(self, *, state):
        self.run_judge_turn_calls += 1
        verdict = VerdictRecord(
            guilty=True,
            reasoning="The prosecution's evidence was more convincing.",
            prosecution_score=8,
            defense_score=5,
            verdict_text=(
                "VERDICT: GUILTY\n"
                "Reasoning: The prosecution's evidence was more convincing.\n"
                "Scores - Prosecution: 8/10, Defense: 5/10"
            ),
        )
        turn = TurnRecord(
            turn_index=len(state.transcript) + 1,
            cycle_number=state.current_cycle,
            actor_role=ActorRole.JUDGE,
            controller=ActorController.AI,
            text=verdict.verdict_text,
            attached_evidence_ids=[],
        )
        return AIRunnerJudgeResult(turn=turn, verdict=verdict, system_events=[])


def _evidence_card(code: str, role: EvidenceRole) -> EvidenceCard:
    return EvidenceCard(code=code, title=f"Title {code}", description=f"Description {code}", evidence_type="Document", assigned_role=role)


def _case_file() -> CaseFileBundle:
    return CaseFileBundle(
        summary=CaseSummary(crime="Theft", charges=["Grand theft"], background_story="A story."),
        prosecution_evidence=[_evidence_card("P-1", EvidenceRole.PROSECUTION), _evidence_card("P-2", EvidenceRole.PROSECUTION)],
        defense_evidence=[_evidence_card("D-1", EvidenceRole.DEFENSE), _evidence_card("D-2", EvidenceRole.DEFENSE)],
    )


def _config(max_rounds: int = 2, allow_evidence_reuse: bool = False) -> MatchConfig:
    return MatchConfig(user_prompt="A case prompt.", max_rounds=max_rounds, allow_evidence_reuse=allow_evidence_reuse)


class TestFullAIMatchPlaythrough:
    def test_completes_with_a_verdict_after_max_rounds(self):
        runner = FakeAIRunner()
        state = create_match_state(config=_config(max_rounds=2), actors=ActorConfiguration(), case_file=_case_file(), ai_runner=runner)

        result = progress_until_pause_or_completion(state=state, ai_runner=runner)

        assert result.action == ProgressAction.MATCH_COMPLETED
        assert result.state.status == MatchStatus.COMPLETED
        assert result.state.verdict is not None
        assert len(result.state.transcript) == 2 * 2 + 1  # 2 rounds * (prosecution + defense) + judge
        assert result.state.transcript[-1].actor_role == ActorRole.JUDGE
        assert runner.run_judge_turn_calls == 1

    def test_evidence_attached_by_ai_gets_marked_used_and_unavailable_next_round(self):
        runner = FakeAIRunner(attach_evidence=True)
        state = create_match_state(config=_config(max_rounds=2), actors=ActorConfiguration(), case_file=_case_file(), ai_runner=runner)

        result = progress_until_pause_or_completion(state=state, ai_runner=runner)

        prosecution_used = {item.code for item in result.state.case_file.prosecution_evidence if item.is_used}
        defense_used = {item.code for item in result.state.case_file.defense_evidence if item.is_used}
        assert prosecution_used == {"P-1", "P-2"}
        assert defense_used == {"D-1", "D-2"}

    def test_allow_evidence_reuse_keeps_the_same_item_available_every_round(self):
        runner = FakeAIRunner(attach_evidence=True)
        state = create_match_state(
            config=_config(max_rounds=2, allow_evidence_reuse=True), actors=ActorConfiguration(), case_file=_case_file(), ai_runner=runner
        )

        result = progress_until_pause_or_completion(state=state, ai_runner=runner)

        prosecution_turns = [t for t in result.state.transcript if t.actor_role == ActorRole.PROSECUTION]
        assert all(t.attached_evidence_ids == ["P-1"] for t in prosecution_turns)


class TestHumanTurnHandling:
    def test_pauses_for_human_prosecution_turn_without_invoking_the_ai_runner(self):
        runner = FakeAIRunner()
        actors = ActorConfiguration(prosecution=ActorController.HUMAN)
        state = create_match_state(config=_config(), actors=actors, case_file=_case_file(), ai_runner=runner)

        result = progress_match_state(state=state, ai_runner=runner)

        assert result.action == ProgressAction.AWAITING_HUMAN_TURN
        assert result.waiting_for_actor == ActorRole.PROSECUTION
        assert runner.run_actor_turn_calls == []

    def test_accepts_a_valid_human_turn_and_advances_to_defense(self):
        actors = ActorConfiguration(prosecution=ActorController.HUMAN)
        state = create_match_state(config=_config(), actors=actors, case_file=_case_file(), ai_runner=FakeAIRunner())

        human_turn = HumanTurnInput(actor_role=ActorRole.PROSECUTION, text="My opening argument.", attached_evidence_ids=["P-1"])
        result = progress_match_state(state=state, human_turn=human_turn)

        assert result.action == ProgressAction.HUMAN_TURN_COMPLETED
        assert result.state.next_actor == ActorRole.DEFENSE
        assert result.state.transcript[-1].text == "My opening argument."
        used = {item.code for item in result.state.case_file.prosecution_evidence if item.is_used}
        assert used == {"P-1"}

    def test_rejects_more_than_one_attached_evidence_item(self):
        actors = ActorConfiguration(prosecution=ActorController.HUMAN)
        state = create_match_state(config=_config(), actors=actors, case_file=_case_file(), ai_runner=FakeAIRunner())

        human_turn = HumanTurnInput(actor_role=ActorRole.PROSECUTION, text="Argument.", attached_evidence_ids=["P-1", "P-2"])
        with pytest.raises(ValueError, match="At most 1 evidence item"):
            progress_match_state(state=state, human_turn=human_turn)

    def test_rejects_an_evidence_id_that_does_not_belong_to_this_role(self):
        actors = ActorConfiguration(prosecution=ActorController.HUMAN)
        state = create_match_state(config=_config(), actors=actors, case_file=_case_file(), ai_runner=FakeAIRunner())

        human_turn = HumanTurnInput(actor_role=ActorRole.PROSECUTION, text="Argument.", attached_evidence_ids=["D-1"])
        with pytest.raises(ValueError, match="Invalid evidence IDs"):
            progress_match_state(state=state, human_turn=human_turn)


class TestAIEvidenceHardEnforcement:
    """progress_match_state has its own evidence cap, independent of validate_turn_output --
    this is the backend's last line of defense if an AIRunnerPort implementation misbehaves."""

    def test_caps_to_a_single_evidence_item_even_if_the_runner_returns_more(self):
        runner = FakeAIRunner(attached_ids_override=["P-1", "P-2"])
        state = create_match_state(config=_config(), actors=ActorConfiguration(), case_file=_case_file(), ai_runner=runner)

        result = progress_match_state(state=state, ai_runner=runner)

        assert result.latest_turn.attached_evidence_ids == ["P-1"]
        used = {item.code for item in result.state.case_file.prosecution_evidence if item.is_used}
        assert used == {"P-1"}

    def test_drops_an_evidence_id_the_runner_invents_that_is_not_available(self):
        runner = FakeAIRunner(attached_ids_override=["NOT-REAL"])
        state = create_match_state(config=_config(), actors=ActorConfiguration(), case_file=_case_file(), ai_runner=runner)

        result = progress_match_state(state=state, ai_runner=runner)

        assert result.latest_turn.attached_evidence_ids == []


class TestQuitAndCompletedHandling:
    def test_quitting_mid_match_marks_status_and_reason(self):
        runner = FakeAIRunner()
        state = create_match_state(config=_config(), actors=ActorConfiguration(), case_file=_case_file(), ai_runner=runner)
        progressed = progress_match_state(state=state, ai_runner=runner).state

        result = quit_match_state(state=progressed, actor_role=ActorRole.PROSECUTION, reason="Player forfeited.")

        assert result.action == ProgressAction.MATCH_QUIT
        assert result.state.status == MatchStatus.QUIT
        assert result.state.quit_reason == "Player forfeited."

    def test_progressing_a_quit_match_is_a_no_op(self):
        state = create_match_state(config=_config(), actors=ActorConfiguration(), case_file=_case_file(), ai_runner=FakeAIRunner())
        quit_state = quit_match_state(state=state, reason="done").state

        result = progress_match_state(state=quit_state, ai_runner=FakeAIRunner())

        assert result.action == ProgressAction.MATCH_QUIT
        assert result.state is quit_state

    def test_progressing_a_completed_match_is_a_no_op(self):
        runner = FakeAIRunner()
        state = create_match_state(config=_config(max_rounds=1), actors=ActorConfiguration(), case_file=_case_file(), ai_runner=runner)
        completed = progress_until_pause_or_completion(state=state, ai_runner=runner).state
        assert completed.status == MatchStatus.COMPLETED

        result = progress_match_state(state=completed, ai_runner=runner)

        assert result.action == ProgressAction.MATCH_COMPLETED
        assert result.latest_turn == completed.transcript[-1]


class TestSnapshotIsolation:
    def test_get_match_snapshot_returns_an_independent_deep_copy(self):
        runner = FakeAIRunner()
        state = create_match_state(config=_config(), actors=ActorConfiguration(), case_file=_case_file(), ai_runner=runner)
        progressed = progress_match_state(state=state, ai_runner=runner).state
        original_length = len(progressed.transcript)

        snapshot = get_match_snapshot_state(progressed)
        snapshot.transcript.append(progressed.transcript[0])

        assert len(snapshot.transcript) == original_length + 1
        assert len(progressed.transcript) == original_length
