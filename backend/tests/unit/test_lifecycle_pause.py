from __future__ import annotations

from backend_integration.models.actors import ActorConfiguration, ActorController, ActorRole
from backend_integration.models.match import MatchStatus, ProgressAction
from backend_integration.services.lifecycle import progress_until_pause_or_completion
from tests.unit.helpers import build_state, FixedAIRunner

def test_progress_until_pause_or_completion_waits_for_human_defense() -> None:
    state = build_state(
        actors=ActorConfiguration(
            prosecution=ActorController.AI,
            defense=ActorController.HUMAN,
            judge=ActorController.AI,
        )
    )

    result = progress_until_pause_or_completion(state=state, ai_runner=FixedAIRunner())

    assert result.action == ProgressAction.AWAITING_HUMAN_TURN
    assert result.waiting_for_actor == ActorRole.DEFENSE
    assert result.latest_turn is not None
    assert result.latest_turn.actor_role == ActorRole.PROSECUTION
    assert result.state.next_actor == ActorRole.DEFENSE
    assert result.state.status == MatchStatus.AWAITING_HUMAN_TURN
    assert len(result.state.transcript) == 1

def test_progress_until_pause_or_completion_waits_for_human_judge_at_final_cycle() -> None:
    state = build_state(
        actors=ActorConfiguration(
            prosecution=ActorController.AI,
            defense=ActorController.AI,
            judge=ActorController.HUMAN,
        ),
        max_rounds=1,
    )

    result = progress_until_pause_or_completion(state=state, ai_runner=FixedAIRunner())

    assert result.action == ProgressAction.AWAITING_HUMAN_VERDICT
    assert result.waiting_for_actor == ActorRole.JUDGE
    assert result.latest_turn is not None
    assert result.latest_turn.actor_role == ActorRole.DEFENSE
    assert result.state.next_actor == ActorRole.JUDGE
    assert result.state.status == MatchStatus.AWAITING_HUMAN_VERDICT
    assert [turn.actor_role for turn in result.state.transcript] == [
        ActorRole.PROSECUTION,
        ActorRole.DEFENSE,
    ]
