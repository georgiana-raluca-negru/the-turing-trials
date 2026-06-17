from __future__ import annotations

import pytest

from backend_integration.models.actors import ActorConfiguration, ActorController, ActorRole
from backend_integration.models.match import MatchStatus, ProgressAction
from backend_integration.models.turns import HumanTurnInput
from backend_integration.services.lifecycle import progress_match_state
from tests.unit.helpers import build_state

def test_progress_match_state_rejects_multiple_unique_human_evidence_ids() -> None:
    state = build_state(
        actors=ActorConfiguration(
            prosecution=ActorController.AI,
            defense=ActorController.HUMAN,
            judge=ActorController.AI,
        ),
        next_actor=ActorRole.DEFENSE,
    )

    with pytest.raises(ValueError, match="At most 1 evidence item"):
        progress_match_state(
            state=state,
            human_turn=HumanTurnInput(
                actor_role=ActorRole.DEFENSE,
                text="The defense cites too many records.",
                attached_evidence_ids=["DEF-1", "DEF-2"],
            ),
        )

def test_progress_match_state_deduplicates_human_evidence_and_advances_turn() -> None:
    state = build_state(
        actors=ActorConfiguration(
            prosecution=ActorController.AI,
            defense=ActorController.HUMAN,
            judge=ActorController.AI,
        ),
        next_actor=ActorRole.DEFENSE,
    )

    result = progress_match_state(
        state=state,
        human_turn=HumanTurnInput(
            actor_role=ActorRole.DEFENSE,
            text="The defense uses one card once.",
            attached_evidence_ids=["DEF-1", "DEF-1"],
        ),
    )

    used_card = next(card for card in result.state.case_file.defense_evidence if card.code == "DEF-1")

    assert result.action == ProgressAction.HUMAN_TURN_COMPLETED
    assert result.latest_turn is not None
    assert result.latest_turn.attached_evidence_ids == ["DEF-1"]
    assert used_card.is_used is True
    assert used_card.used_in_turn_index == 1
    assert result.state.current_cycle == 2
    assert result.state.next_actor == ActorRole.PROSECUTION
    assert result.state.status == MatchStatus.IN_PROGRESS
