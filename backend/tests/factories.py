from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.models.match import Match, MatchStatus, PlayerRole, Verdict
from app.models.user import User
from backend_integration.models.actors import ActorConfiguration, ActorController, ActorRole
from backend_integration.models.case_file import CaseFileBundle, CaseSummary, EvidenceCard, EvidenceRole
from backend_integration.models.match import MatchConfig, MatchRuntimeState, MatchStatus as RuntimeMatchStatus
from backend_integration.models.turns import TurnRecord, VerdictRecord


def build_case_file_bundle() -> CaseFileBundle:
    return CaseFileBundle(
        summary=CaseSummary(
            crime="Museum Theft",
            charges=["Grand Larceny", "Destruction of Property"],
            background_story=(
                "A valuable painting vanished during a staged gala evacuation, "
                "leaving both prosecution and defense with plausible narratives."
            ),
        ),
        prosecution_evidence=[
            EvidenceCard(
                code="EVD-PRO-001",
                title="Surveillance Footage",
                description="Camera footage places the accused near the west wing minutes before the theft.",
                evidence_type="video",
                assigned_role=EvidenceRole.PROSECUTION,
            ),
            EvidenceCard(
                code="EVD-PRO-002",
                title="Glass Fragments",
                description="Fragments from the display case contain the accused's glove fibers.",
                evidence_type="forensic",
                assigned_role=EvidenceRole.PROSECUTION,
            ),
            EvidenceCard(
                code="EVD-PRO-003",
                title="Security Log Gap",
                description="A twelve-minute alarm suppression window was triggered with the accused's badge.",
                evidence_type="digital",
                assigned_role=EvidenceRole.PROSECUTION,
            ),
            EvidenceCard(
                code="EVD-PRO-004",
                title="Witness Statement",
                description="A guard reports seeing the accused carrying a wrapped frame.",
                evidence_type="testimony",
                assigned_role=EvidenceRole.PROSECUTION,
            ),
        ],
        defense_evidence=[
            EvidenceCard(
                code="EVD-DEF-001",
                title="Badge Clone Report",
                description="IT records show the accused's badge credentials were duplicated two days earlier.",
                evidence_type="digital",
                assigned_role=EvidenceRole.DEFENSE,
            ),
            EvidenceCard(
                code="EVD-DEF-002",
                title="Alibi Receipt",
                description="A cafe receipt timestamp places the accused off-site during the first alarm signal.",
                evidence_type="document",
                assigned_role=EvidenceRole.DEFENSE,
            ),
            EvidenceCard(
                code="EVD-DEF-003",
                title="Restoration Contract",
                description="The accused had authorized access to wrapped frames because of scheduled restoration work.",
                evidence_type="document",
                assigned_role=EvidenceRole.DEFENSE,
            ),
            EvidenceCard(
                code="EVD-DEF-004",
                title="Alternate Suspect Tip",
                description="An anonymous tip identifies a rival curator with financial motives.",
                evidence_type="testimony",
                assigned_role=EvidenceRole.DEFENSE,
            ),
        ],
        shared_evidence=[
            EvidenceCard(
                code="EVD-SHR-001",
                title="Gallery Floor Plan",
                description="The west wing connects directly to an unmonitored loading corridor.",
                evidence_type="document",
                assigned_role=EvidenceRole.SHARED,
            )
        ],
    )


def build_runtime_state(
    *,
    player_role: PlayerRole = PlayerRole.DEFENSE_ATTORNEY,
    current_cycle: int = 1,
    next_actor: ActorRole = ActorRole.PROSECUTION,
    transcript: list[TurnRecord] | None = None,
) -> MatchRuntimeState:
    actors = {
        PlayerRole.DEFENSE_ATTORNEY: ActorConfiguration(
            prosecution=ActorController.AI,
            defense=ActorController.HUMAN,
            judge=ActorController.AI,
        ),
        PlayerRole.PROSECUTOR: ActorConfiguration(
            prosecution=ActorController.HUMAN,
            defense=ActorController.AI,
            judge=ActorController.AI,
        ),
        PlayerRole.JUDGE: ActorConfiguration(
            prosecution=ActorController.AI,
            defense=ActorController.AI,
            judge=ActorController.HUMAN,
        ),
        PlayerRole.SPECTATOR: ActorConfiguration(),
    }[player_role]

    return MatchRuntimeState(
        config=MatchConfig(
            match_id=str(uuid.uuid4()),
            user_prompt="A museum theft with disputed forensic evidence.",
            max_rounds=3,
            allow_evidence_reuse=False,
        ),
        actors=actors,
        case_file=build_case_file_bundle(),
        status=RuntimeMatchStatus.IN_PROGRESS,
        current_cycle=current_cycle,
        next_actor=next_actor,
        transcript=transcript or [],
        system_events=[],
    )


def build_turn_record(
    *,
    actor_role: ActorRole = ActorRole.PROSECUTION,
    controller: ActorController = ActorController.AI,
    cycle_number: int = 1,
    turn_index: int = 1,
    text: str = "A deterministic test argument.",
    attached_evidence_ids: list[str] | None = None,
    skipped: bool = False,
    system_note: str | None = None,
) -> TurnRecord:
    return TurnRecord(
        turn_index=turn_index,
        cycle_number=cycle_number,
        actor_role=actor_role,
        controller=controller,
        text=text,
        attached_evidence_ids=attached_evidence_ids or [],
        skipped=skipped,
        system_note=system_note,
    )


def build_verdict_record(*, guilty: bool = False) -> VerdictRecord:
    verdict_text = (
        f"VERDICT: {'GUILTY' if guilty else 'NOT GUILTY'}\n"
        "Reasoning: The evidence leaves room for reasonable doubt.\n"
        "Scores - Prosecution: 6/10, Defense: 8/10"
    )
    return VerdictRecord(
        guilty=guilty,
        reasoning="The evidence leaves room for reasonable doubt.",
        prosecution_score=6,
        defense_score=8,
        verdict_text=verdict_text,
    )


def build_user(
    *,
    username: str | None = None,
    email: str | None = None,
    hashed_password: str = "hashed-password",
) -> User:
    suffix = uuid.uuid4().hex[:8]
    return User(
        username=username or f"user_{suffix}",
        email=email or f"{suffix}@example.com",
        hashed_password=hashed_password,
        is_active=True,
        is_verified=True,
        total_matches=0,
        total_wins=0,
    )


def build_match(
    *,
    player_id: uuid.UUID,
    player_role: PlayerRole = PlayerRole.DEFENSE_ATTORNEY,
    status: MatchStatus = MatchStatus.LOBBY,
    total_rounds: int = 3,
    player_prompt: str = "A museum theft with disputed forensic evidence.",
) -> Match:
    return Match(
        player_id=player_id,
        player_prompt=player_prompt,
        player_role=player_role,
        total_rounds=total_rounds,
        status=status,
        verdict=Verdict.PENDING,
        created_at=datetime.now(timezone.utc),
    )
