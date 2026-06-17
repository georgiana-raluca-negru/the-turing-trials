import pytest
from ai_engine.models.schemas import Argument, CaseContext, CaseFile, Evidence, TurnOutput, Verdict
from ai_engine.utils.structured_outputs import (
    SemanticValidationError,
    build_judge_fallback_argument,
    build_missed_turn_argument,
    mark_evidence_used,
    render_history,
    validate_case_file,
    validate_turn_output,
    validate_verdict,
)

pytestmark = pytest.mark.unit


def _evidence(id_: str, is_used: bool = False) -> Evidence:
    return Evidence(id=id_, title=f"Title {id_}", description=f"Description {id_}", type="Document", is_used=is_used)


def _case_context() -> CaseContext:
    return CaseContext(crime="Theft", charges=["Grand theft"], background_story="A story.")


class TestRenderHistory:
    def test_empty_history_returns_placeholder(self):
        assert render_history([]) == "The trial has just begun."

    def test_formats_each_message_as_speaker_colon_text(self):
        messages = [
            Argument(speaker="Prosecutor", text="The defendant is guilty."),
            Argument(speaker="Defense", text="My client is innocent."),
        ]
        assert render_history(messages) == (
            "Prosecutor: The defendant is guilty.\n"
            "Defense: My client is innocent."
        )

    def test_does_not_render_attached_evidence_ids(self):
        message = Argument(speaker="Prosecutor", text="See exhibit A.", attached_evidence_ids=["EVD-001"])
        assert "EVD-001" not in render_history([message])


class TestMarkEvidenceUsed:
    def test_marks_only_referenced_ids_as_used(self):
        evidence_list = [_evidence("EVD-001"), _evidence("EVD-002")]
        updated = mark_evidence_used(evidence_list, ["EVD-001"])
        assert updated[0].is_used is True
        assert updated[1].is_used is False

    def test_does_not_unmark_already_used_evidence(self):
        evidence_list = [_evidence("EVD-001", is_used=True)]
        updated = mark_evidence_used(evidence_list, [])
        assert updated[0].is_used is True

    def test_returns_new_list_without_mutating_input(self):
        evidence_list = [_evidence("EVD-001")]
        mark_evidence_used(evidence_list, ["EVD-001"])
        assert evidence_list[0].is_used is False


class TestValidateCaseFile:
    def _case_file(self, prosecution_count=3, defense_count=3):
        prosecution = [_evidence(f"P-{i}") for i in range(prosecution_count)]
        defense = [_evidence(f"D-{i}") for i in range(defense_count)]
        return CaseFile(case_summary=_case_context(), prosecution_evidence=prosecution, defense_evidence=defense)

    def test_accepts_valid_case_file(self):
        case_file = self._case_file()
        assert validate_case_file(case_file) is case_file

    def test_rejects_too_few_prosecution_evidence(self):
        case_file = self._case_file(prosecution_count=1)
        with pytest.raises(SemanticValidationError, match="prosecution evidence"):
            validate_case_file(case_file)

    def test_rejects_too_few_defense_evidence(self):
        case_file = self._case_file(defense_count=1)
        with pytest.raises(SemanticValidationError, match="defense evidence"):
            validate_case_file(case_file)

    def test_rejects_duplicate_ids_within_a_side(self):
        case_file = CaseFile(
            case_summary=_case_context(),
            prosecution_evidence=[_evidence("P-0"), _evidence("P-0"), _evidence("P-1")],
            defense_evidence=[_evidence(f"D-{i}") for i in range(3)],
        )
        with pytest.raises(SemanticValidationError, match="duplicate IDs"):
            validate_case_file(case_file)

    def test_rejects_overlapping_ids_across_sides(self):
        case_file = CaseFile(
            case_summary=_case_context(),
            prosecution_evidence=[_evidence("SHARED"), _evidence("P-1"), _evidence("P-2")],
            defense_evidence=[_evidence("SHARED"), _evidence("D-1"), _evidence("D-2")],
        )
        with pytest.raises(SemanticValidationError, match="Overlaps"):
            validate_case_file(case_file)


class TestValidateTurnOutput:
    def test_strips_whitespace_from_text(self):
        turn_output = TurnOutput(text="  hello  ", attached_evidence_ids=[])
        result = validate_turn_output(turn_output, available_evidence_ids=[])
        assert result.text == "hello"

    def test_drops_ids_not_in_available_evidence(self):
        turn_output = TurnOutput(text="argument", attached_evidence_ids=["EVD-999"])
        result = validate_turn_output(turn_output, available_evidence_ids=["EVD-001"])
        assert result.attached_evidence_ids == []

    def test_caps_attached_evidence_to_at_most_one(self):
        turn_output = TurnOutput(text="argument", attached_evidence_ids=["EVD-001", "EVD-002"])
        result = validate_turn_output(turn_output, available_evidence_ids=["EVD-001", "EVD-002"])
        assert result.attached_evidence_ids == ["EVD-001"]

    def test_deduplicates_repeated_ids_before_capping(self):
        turn_output = TurnOutput(text="argument", attached_evidence_ids=["EVD-001", "EVD-001"])
        result = validate_turn_output(turn_output, available_evidence_ids=["EVD-001"])
        assert result.attached_evidence_ids == ["EVD-001"]

    def test_keeps_single_valid_id(self):
        turn_output = TurnOutput(text="argument", attached_evidence_ids=["EVD-001"])
        result = validate_turn_output(turn_output, available_evidence_ids=["EVD-001"])
        assert result.attached_evidence_ids == ["EVD-001"]

    def test_strips_raw_evidence_code_written_in_parentheses(self):
        turn_output = TurnOutput(
            text="the security footage (EVD-001) shows a figure near the store.",
            attached_evidence_ids=["EVD-001"],
        )
        result = validate_turn_output(turn_output, available_evidence_ids=["EVD-001"])
        assert "EVD-001" not in result.text
        assert result.text == "the security footage shows a figure near the store."

    def test_strips_evidence_code_even_when_not_attached(self):
        turn_output = TurnOutput(
            text="the receipt (EVD-002), unlike the footage (EVD-001), proves nothing.",
            attached_evidence_ids=["EVD-002"],
        )
        result = validate_turn_output(turn_output, available_evidence_ids=["EVD-001", "EVD-002"])
        assert "EVD-001" not in result.text
        assert "EVD-002" not in result.text
        assert result.text == "the receipt, unlike the footage, proves nothing."

    def test_does_not_strip_codes_outside_the_available_set(self):
        turn_output = TurnOutput(text="mentions EVD-999 which isn't a real code.", attached_evidence_ids=[])
        result = validate_turn_output(turn_output, available_evidence_ids=["EVD-001"])
        assert "EVD-999" in result.text

    def test_falls_back_to_original_text_if_stripping_empties_it(self):
        turn_output = TurnOutput(text="(EVD-001)", attached_evidence_ids=["EVD-001"])
        result = validate_turn_output(turn_output, available_evidence_ids=["EVD-001"])
        assert result.text == "(EVD-001)"


class TestValidateVerdict:
    def test_strips_whitespace_from_reasoning(self):
        verdict = Verdict(guilty=True, reasoning="  guilty because...  ", defense_score=5, prosecution_score=8)
        result = validate_verdict(verdict)
        assert result.reasoning == "guilty because..."

    def test_rejects_blank_reasoning(self):
        # Verdict's own str_strip_whitespace + min_length would normally reject this
        # at construction time, so bypass validation to exercise validate_verdict's
        # own defense-in-depth check directly.
        verdict = Verdict.model_construct(guilty=True, reasoning="   ", defense_score=5, prosecution_score=8)
        with pytest.raises(SemanticValidationError, match="cannot be empty"):
            validate_verdict(verdict)


class TestFallbackArguments:
    def test_build_missed_turn_argument_marks_text_and_warns(self):
        argument, warning = build_missed_turn_argument("Prosecutor", "boom")
        assert argument.speaker == "Prosecutor"
        assert "[TURN MISSED]" in argument.text
        assert argument.attached_evidence_ids == []
        assert "boom" in warning

    def test_build_judge_fallback_argument_marks_verdict_unavailable(self):
        argument, warning = build_judge_fallback_argument("boom")
        assert argument.speaker == "Judge"
        assert "VERDICT UNAVAILABLE" in argument.text
        assert "boom" in warning
