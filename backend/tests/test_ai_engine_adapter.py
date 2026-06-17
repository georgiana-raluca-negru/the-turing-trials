import pytest

pytestmark = pytest.mark.unit

from backend_integration.adapters.ai_engine import _build_message_history, _parse_verdict_text
from backend_integration.models.actors import ActorConfiguration, ActorController, ActorRole
from backend_integration.models.case_file import CaseFileBundle, CaseSummary, EvidenceCard, EvidenceRole
from backend_integration.models.match import MatchConfig, MatchRuntimeState
from backend_integration.models.turns import TurnRecord


def _evidence_card(code: str, role: EvidenceRole, title: str = None, description: str = None) -> EvidenceCard:
    return EvidenceCard(
        code=code,
        title=title or f"Title {code}",
        description=description or f"Description {code}",
        evidence_type="Document",
        assigned_role=role,
    )


def _turn(
    actor_role: ActorRole,
    text: str,
    *,
    turn_index: int = 1,
    attached_evidence_ids: list[str] | None = None,
    system_note: str | None = None,
) -> TurnRecord:
    return TurnRecord(
        turn_index=turn_index,
        cycle_number=1,
        actor_role=actor_role,
        controller=ActorController.AI,
        text=text,
        attached_evidence_ids=attached_evidence_ids or [],
        system_note=system_note,
    )


def _state(transcript: list[TurnRecord], evidence_cards: list[EvidenceCard] | None = None) -> MatchRuntimeState:
    cards = evidence_cards or []
    return MatchRuntimeState(
        config=MatchConfig(user_prompt="A case prompt."),
        actors=ActorConfiguration(),
        case_file=CaseFileBundle(
            summary=CaseSummary(crime="Theft", charges=["Grand theft"], background_story="A story."),
            prosecution_evidence=[c for c in cards if c.assigned_role == EvidenceRole.PROSECUTION],
            defense_evidence=[c for c in cards if c.assigned_role == EvidenceRole.DEFENSE],
            shared_evidence=[c for c in cards if c.assigned_role == EvidenceRole.SHARED],
        ),
        transcript=transcript,
    )


class TestBuildMessageHistory:
    def test_judge_turns_are_excluded(self):
        state = _state([_turn(ActorRole.JUDGE, "VERDICT: GUILTY")])
        assert _build_message_history(state) == []

    def test_maps_actor_roles_to_speaker_names(self):
        state = _state([
            _turn(ActorRole.PROSECUTION, "Opening statement.", turn_index=1),
            _turn(ActorRole.DEFENSE, "Rebuttal.", turn_index=2),
        ])
        messages = _build_message_history(state)
        assert [m.speaker for m in messages] == ["Prosecutor", "Defense"]

    def test_appends_evidence_title_and_description_when_attached(self):
        card = _evidence_card("EVD-001", EvidenceRole.PROSECUTION, title="Bloody Glove", description="Found at the scene.")
        state = _state(
            [_turn(ActorRole.PROSECUTION, "See this evidence.", attached_evidence_ids=["EVD-001"])],
            evidence_cards=[card],
        )
        [message] = _build_message_history(state)
        assert "See this evidence." in message.text
        assert "[Evidence submitted: Bloody Glove — Found at the scene.]" in message.text

    def test_looks_up_evidence_across_all_three_roles(self):
        shared_card = _evidence_card("EVD-SHARED", EvidenceRole.SHARED, title="Security Footage")
        state = _state(
            [_turn(ActorRole.DEFENSE, "Consider the footage.", attached_evidence_ids=["EVD-SHARED"])],
            evidence_cards=[shared_card],
        )
        [message] = _build_message_history(state)
        assert "Security Footage" in message.text

    def test_unknown_evidence_code_is_silently_ignored(self):
        state = _state(
            [_turn(ActorRole.PROSECUTION, "See exhibit X.", attached_evidence_ids=["DOES-NOT-EXIST"])],
            evidence_cards=[],
        )
        [message] = _build_message_history(state)
        assert message.text == "See exhibit X."

    def test_turn_without_attached_evidence_is_left_unchanged(self):
        state = _state([_turn(ActorRole.PROSECUTION, "No evidence here.")])
        [message] = _build_message_history(state)
        assert message.text == "No evidence here."

    def test_objection_raised_inserts_system_notice_after_the_turn(self):
        state = _state([
            _turn(ActorRole.PROSECUTION, "Irrelevant point.", system_note="[OBJECTION RAISED]"),
        ])
        messages = _build_message_history(state)
        assert len(messages) == 2
        assert messages[0].speaker == "Prosecutor"
        assert messages[1].speaker == "System"
        assert "OBJECTION" in messages[1].text

    def test_no_system_notice_when_no_objection(self):
        state = _state([_turn(ActorRole.PROSECUTION, "Calm statement.")])
        messages = _build_message_history(state)
        assert len(messages) == 1


class TestParseVerdictText:
    def test_parses_guilty_verdict_with_scores(self):
        text = (
            "VERDICT: GUILTY\n"
            "Reasoning: The evidence was overwhelming.\n"
            "Scores - Prosecution: 8/10, Defense: 4/10"
        )
        verdict = _parse_verdict_text(text)
        assert verdict.guilty is True
        assert verdict.reasoning == "The evidence was overwhelming."
        assert verdict.prosecution_score == 8
        assert verdict.defense_score == 4
        assert verdict.verdict_text == text

    def test_parses_not_guilty_verdict(self):
        text = (
            "VERDICT: NOT GUILTY\n"
            "Reasoning: Reasonable doubt remains.\n"
            "Scores - Prosecution: 3/10, Defense: 9/10"
        )
        verdict = _parse_verdict_text(text)
        assert verdict.guilty is False
        assert verdict.prosecution_score == 3
        assert verdict.defense_score == 9

    def test_unparseable_text_falls_back_to_full_text_as_reasoning(self):
        text = "VERDICT UNAVAILABLE\nReasoning: The judge failed to return a valid structured verdict."
        verdict = _parse_verdict_text(text)
        assert verdict.guilty is None
        assert verdict.prosecution_score is None
        assert verdict.defense_score is None
        assert verdict.verdict_text == text
