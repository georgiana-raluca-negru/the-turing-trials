from __future__ import annotations

from backend_integration.models.actors import ActorConfiguration, ActorController, ActorRole
from backend_integration.models.match import MatchConfig, MatchStatus
from backend_integration.services.lifecycle import create_match_state
from tests.unit.helpers import build_case_file

def test_create_match_state_marks_human_prosecutor_as_waiting() -> None:
    state = create_match_state(
        config=MatchConfig(match_id="match-1", user_prompt="Museum theft"),
        actors=ActorConfiguration(
            prosecution=ActorController.HUMAN,
            defense=ActorController.AI,
            judge=ActorController.AI,
        ),
        case_file=build_case_file(),
    )

    assert state.status == MatchStatus.AWAITING_HUMAN_TURN
    assert state.next_actor == ActorRole.PROSECUTION
    assert state.current_cycle == 1
