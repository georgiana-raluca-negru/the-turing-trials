import os

import pytest

from ai_engine.agents.ai_clerk import generate_case_node

pytestmark = [
    pytest.mark.eval,
    pytest.mark.skipif(
        not os.getenv("OPENAI_API_KEY"),
        reason="OPENAI_API_KEY not configured; skipping live LLM eval.",
    ),
]


def _run_clerk(user_prompt: str) -> dict:
    return generate_case_node({"user_prompt": user_prompt, "allow_evidence_reuse": False})


class TestAIClerkEval:
    def test_generates_a_complete_balanced_case_file(self):
        result = _run_clerk(
            "A warehouse fire that investigators suspect was set to destroy evidence of insurance fraud."
        )

        assert result["case_summary"].crime
        assert result["case_summary"].charges
        assert result["case_summary"].background_story

        assert len(result["prosecution_evidence"]) >= 3
        assert len(result["defense_evidence"]) >= 3

        prosecution_ids = {e.id for e in result["prosecution_evidence"]}
        defense_ids = {e.id for e in result["defense_evidence"]}
        assert not (prosecution_ids & defense_ids)

        for evidence in result["prosecution_evidence"] + result["defense_evidence"]:
            assert len(evidence.title.split()) >= 2, f"Evidence title too generic: {evidence.title!r}"
            assert len(evidence.description) >= 20, f"Evidence description too thin: {evidence.description!r}"

    def test_background_story_reflects_the_user_prompt(self):
        result = _run_clerk("A dispute over who owns a rare vintage guitar after a divorce.")

        background = result["case_summary"].background_story.lower()
        assert "guitar" in background or "divorce" in background, (
            f"Background story doesn't reflect the prompt: {result['case_summary'].background_story!r}"
        )
