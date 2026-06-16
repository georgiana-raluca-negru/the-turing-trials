import os
import re

import pytest

from ai_engine.agents.defense import defense_turn_node
from ai_engine.agents.prosecutor import prosecutor_turn_node
from ai_engine.models.schemas import CaseContext, Evidence

pytestmark = [
    pytest.mark.eval,
    pytest.mark.skipif(
        not os.getenv("OPENAI_API_KEY"),
        reason="OPENAI_API_KEY not configured; skipping live LLM eval.",
    ),
]

_EVIDENCE_CODE_PATTERN = re.compile(r"EVD-\d{3}")

_CASE_SUMMARY = CaseContext(
    crime="Burglary",
    charges=["Breaking and entering", "Grand larceny"],
    background_story=(
        "The defendant is accused of breaking into a jewelry store at night and stealing a "
        "diamond necklace. A neighbor reports seeing a person matching the defendant's "
        "description near the store around the time of the break-in."
    ),
)


def _evidence(id_: str, title: str, description: str) -> Evidence:
    return Evidence(id=id_, title=title, description=description, type="Document")


def _base_state(evidence_list: list[Evidence]) -> dict:
    return {
        "user_prompt": "irrelevant for this eval",
        "allow_evidence_reuse": False,
        "case_summary": _CASE_SUMMARY,
        "prosecution_evidence": evidence_list,
        "defense_evidence": evidence_list,
        "messages": [],
        "round_number": 1,
        "system_events": [],
    }


@pytest.mark.parametrize("node", [prosecutor_turn_node, defense_turn_node], ids=["prosecutor", "defense"])
class TestAdvocateEval:
    """Both sides share a prompt template with the exact same evidence rule, so the
    same checks apply to either node -- this is also the rule an earlier bug report
    (referat_mds) found the LLM ignoring: attaching more than one evidence item."""

    def test_attaches_at_most_one_evidence_item(self, node):
        evidence_list = [
            _evidence("EVD-001", "Security Camera Footage", "Shows a figure matching the defendant near the store."),
            _evidence("EVD-002", "Pawn Shop Receipt", "A receipt for a diamond necklace sold the next day."),
            _evidence("EVD-003", "Witness Statement", "A neighbor's account of what they saw that night."),
        ]
        state = _base_state(evidence_list)
        result = node(state)

        argument = result["messages"][-1]
        assert len(argument.attached_evidence_ids) <= 1
        if argument.attached_evidence_ids:
            assert argument.attached_evidence_ids[0] in {e.id for e in evidence_list}

    def test_never_writes_raw_evidence_codes_in_the_argument_text(self, node):
        evidence_list = [
            _evidence("EVD-001", "Security Camera Footage", "Shows a figure matching the defendant near the store."),
            _evidence("EVD-002", "Pawn Shop Receipt", "A receipt for a diamond necklace sold the next day."),
        ]
        state = _base_state(evidence_list)
        result = node(state)

        argument = result["messages"][-1]
        assert not _EVIDENCE_CODE_PATTERN.search(argument.text), (
            f"Argument text leaked a raw evidence ID code: {argument.text!r}"
        )

    def test_produces_a_non_trivial_argument(self, node):
        evidence_list = [
            _evidence("EVD-001", "Security Camera Footage", "Shows a figure matching the defendant near the store."),
        ]
        state = _base_state(evidence_list)
        result = node(state)

        argument = result["messages"][-1]
        assert len(argument.text) >= 40
        assert not argument.text.startswith("[TURN MISSED]")
