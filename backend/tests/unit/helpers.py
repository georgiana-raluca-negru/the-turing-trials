from __future__ import annotations

from dataclasses import dataclass, field

from backend_integration.models.actors import ActorConfiguration, ActorController, ActorRole
from backend_integration.models.case_file import CaseFileBundle, CaseSummary, EvidenceCard, EvidenceRole
from backend_integration.models.match import MatchConfig, MatchRuntimeState, MatchStatus
from backend_integration.models.turns import TurnRecord
from backend_integration.ports.ai_runner import AIRunnerTurnResult

def build_case_file() -> CaseFileBundle:
    return CaseFileBundle(
        summary=CaseSummary(
            crime="Museum Theft",
            charges=["Grand Larceny"],
            background_story="A single disputed timeline drives the case.",
        ),
        prosecution_evidence=[
            EvidenceCard(
                code="PRO-1",
                title="Camera Footage",
                description="Places the accused near the gallery.",
                evidence_type="video",
                assigned_role=EvidenceRole.PROSECUTION,
            )
        ],
        defense_evidence=[
            EvidenceCard(
                code="DEF-1",
                title="Badge Clone Report",
                description="Shows the badge credentials were duplicated.",
                evidence_type="document",
                assigned_role=EvidenceRole.DEFENSE,
            ),
            EvidenceCard(
                code="DEF-2",
                title="Cafe Receipt",
                description="Suggests the accused was elsewhere.",
                evidence_type="document",
                assigned_role=EvidenceRole.DEFENSE,
            ),
        ],
        shared_evidence=[],
    )

def build_state(
    *,
    actors: ActorConfiguration,
    current_cycle: int = 1,
    next_actor: ActorRole = ActorRole.PROSECUTION,
    max_rounds: int = 3,
    transcript: list[TurnRecord] | None = None,
) -> MatchRuntimeState:
    return MatchRuntimeState(
        config=MatchConfig(
            match_id="match-1",
            user_prompt="Museum theft",
            max_rounds=max_rounds,
            allow_evidence_reuse=False,
        ),
        actors=actors,
        case_file=build_case_file(),
        status=MatchStatus.IN_PROGRESS,
        current_cycle=current_cycle,
        next_actor=next_actor,
        transcript=transcript or [],
        system_events=[],
    )

@dataclass
class FixedAIRunner:
    system_events: list[str] = field(default_factory=list)

    def generate_case(self, *, user_prompt: str, allow_evidence_reuse: bool) -> CaseFileBundle:
        return build_case_file()

    def run_actor_turn(self, *, state: MatchRuntimeState, actor_role: ActorRole) -> AIRunnerTurnResult:
        turn = TurnRecord(
            turn_index=len(state.transcript) + 1,
            cycle_number=state.current_cycle,
            actor_role=actor_role,
            controller=ActorController.AI,
            text=f"{actor_role.value} argues.",
            attached_evidence_ids=[],
        )
        return AIRunnerTurnResult(
            turn=turn,
            updated_case_file=state.case_file.model_copy(deep=True),
            system_events=list(self.system_events),
        )
