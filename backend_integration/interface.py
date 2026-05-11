from __future__ import annotations

from backend_integration.models.actors import ActorConfiguration, ActorRole
from backend_integration.models.case_file import CaseFileBundle, EvidenceCard
from backend_integration.models.match import MatchConfig, MatchProgressResult, MatchRuntimeState
from backend_integration.models.turns import HumanJudgeVerdictInput, HumanTurnInput
from backend_integration.ports.ai_runner import AIRunnerPort
from backend_integration.services.lifecycle import (
    create_match_state,
    get_available_evidence_for_role,
    get_match_snapshot_state,
    progress_match_state,
    progress_until_pause_or_completion,
    quit_match_state,
)


def create_match(
    *,
    config: MatchConfig,
    actors: ActorConfiguration,
    case_file: CaseFileBundle | None = None,
    ai_runner: AIRunnerPort | None = None,
) -> MatchRuntimeState:
    return create_match_state(
        config=config,
        actors=actors,
        case_file=case_file,
        ai_runner=ai_runner,
    )


def progress_match(
    *,
    state: MatchRuntimeState,
    ai_runner: AIRunnerPort | None = None,
    human_turn: HumanTurnInput | None = None,
    human_verdict: HumanJudgeVerdictInput | None = None,
) -> MatchProgressResult:
    return progress_match_state(
        state=state,
        ai_runner=ai_runner,
        human_turn=human_turn,
        human_verdict=human_verdict,
    )


def progress_until_human_or_terminal(
    *,
    state: MatchRuntimeState,
    ai_runner: AIRunnerPort | None = None,
) -> MatchProgressResult:
    return progress_until_pause_or_completion(state=state, ai_runner=ai_runner)


def submit_human_turn(
    *,
    state: MatchRuntimeState,
    human_turn: HumanTurnInput,
) -> MatchProgressResult:
    return progress_match_state(state=state, human_turn=human_turn)


def submit_human_verdict(
    *,
    state: MatchRuntimeState,
    human_verdict: HumanJudgeVerdictInput,
) -> MatchProgressResult:
    return progress_match_state(state=state, human_verdict=human_verdict)


def quit_match(
    *,
    state: MatchRuntimeState,
    actor_role: ActorRole | None = None,
    reason: str = "Quit requested.",
) -> MatchProgressResult:
    return quit_match_state(state=state, actor_role=actor_role, reason=reason)


def get_match_snapshot(*, state: MatchRuntimeState) -> MatchRuntimeState:
    return get_match_snapshot_state(state)


def get_available_evidence(*, state: MatchRuntimeState, role: ActorRole) -> list[EvidenceCard]:
    return get_available_evidence_for_role(state, role)
