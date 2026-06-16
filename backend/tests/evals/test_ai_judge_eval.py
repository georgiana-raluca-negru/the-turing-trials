import os
import re

import pytest

from ai_engine.agents.ai_judge import judge_verdict_node
from ai_engine.models.schemas import Argument, CaseContext

pytestmark = [
    pytest.mark.eval,
    pytest.mark.skipif(
        not os.getenv("OPENAI_API_KEY"),
        reason="OPENAI_API_KEY not configured; skipping live LLM eval.",
    ),
]

_CASE_SUMMARY = CaseContext(
    crime="Arson",
    charges=["Arson", "Insurance fraud"],
    background_story="The defendant is accused of burning down their own warehouse to collect insurance money.",
)


def _judge(messages: list[Argument]) -> Argument:
    state = {
        "case_summary": _CASE_SUMMARY,
        "messages": messages,
        "round_number": 4,
        "system_events": [],
    }
    result = judge_verdict_node(state)
    return result["messages"][-1]


def test_judge_verdict_reflects_evidence_visible_in_the_transcript():
    # This mirrors what `_build_message_history` in the backend adapter injects into
    # an argument's text once evidence is attached. It's the regression test for the
    # bug where the Judge couldn't see submitted evidence at all (only `message.text`
    # was rendered into history, never `attached_evidence_ids`).
    messages = [
        Argument(
            speaker="Prosecutor",
            text=(
                "The defendant had a clear financial motive and was seen near the warehouse "
                "minutes before the fire started.\n"
                "[Evidence submitted: Gas Station Receipt — A receipt showing the defendant "
                "purchased five gallons of gasoline two hours before the fire.]"
            ),
        ),
        Argument(
            speaker="Defense",
            text="My client was at a public event with dozens of witnesses at the time of the fire.",
        ),
    ]

    verdict_argument = _judge(messages)

    assert verdict_argument.speaker == "Judge"
    assert re.search(r"VERDICT:\s*(GUILTY|NOT GUILTY)", verdict_argument.text, re.IGNORECASE)
    assert re.search(
        r"Scores\s*-\s*Prosecution:\s*\d+/10,\s*Defense:\s*\d+/10", verdict_argument.text, re.IGNORECASE
    )

    reasoning_lower = verdict_argument.text.lower()
    assert any(keyword in reasoning_lower for keyword in ("gas", "gasoline", "receipt")), (
        "Judge's reasoning never references the evidence visible in the transcript -- "
        f"got: {verdict_argument.text!r}"
    )


def test_judge_reasoning_stays_within_the_prompted_word_budget():
    messages = [
        Argument(speaker="Prosecutor", text="The defendant had motive and opportunity."),
        Argument(speaker="Defense", text="There is no direct evidence linking my client to the fire."),
    ]

    verdict_argument = _judge(messages)

    reasoning_match = re.search(r"Reasoning:\s*(.*?)\nScores", verdict_argument.text, re.IGNORECASE | re.DOTALL)
    assert reasoning_match, f"Could not find a Reasoning section in: {verdict_argument.text!r}"

    # Prompt says "under 250 words"; allow some buffer before flagging it as an eval failure.
    word_count = len(reasoning_match.group(1).split())
    assert word_count <= 280, f"Judge reasoning ran long: {word_count} words"
