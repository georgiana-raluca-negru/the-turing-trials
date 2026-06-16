"""Integration tests for the LangGraph workflow wiring (create_workflow).

These run the real graph -- real node functions, real edges, real conditional
routing, real state threading across turns -- but swap get_llm() for a fake that
returns canned structured output, so no network call or API key is needed. The
goal is to catch breakage in how the four agents are wired together, which the
eval suite (real LLM, one node at a time) and unit tests (pure functions) don't
cover.
"""

import ai_engine.agents.ai_clerk as ai_clerk_module
import ai_engine.agents.ai_judge as ai_judge_module
import ai_engine.agents.defense as defense_module
import ai_engine.agents.prosecutor as prosecutor_module
import pytest
from ai_engine.graph.workflow import create_workflow
from ai_engine.models.schemas import CaseContext, CaseFile, Evidence, TurnOutput, Verdict
from langchain_core.runnables import RunnableLambda

pytestmark = pytest.mark.integration


class _FakeLLM:
    """Stands in for get_llm()'s ChatOpenAI: with_structured_output() returns a
    canned response on the first attempted strategy, so generate_structured_response
    never falls through to a real network call."""

    def __init__(self, response):
        self._response = response

    def with_structured_output(self, schema, method=None, include_raw=False):
        return RunnableLambda(lambda _formatted_prompt: {"raw": None, "parsed": self._response, "parsing_error": None})


@pytest.fixture
def wired_workflow(monkeypatch):
    case_file_response = CaseFile(
        case_summary=CaseContext(crime="Arson", charges=["Arson"], background_story="A warehouse burned down."),
        prosecution_evidence=[
            Evidence(id="P-1", title="Gas Receipt", description="Shows a gasoline purchase.", type="Document"),
            Evidence(id="P-2", title="Witness", description="Saw the defendant nearby.", type="Testimony"),
            Evidence(id="P-3", title="Insurance Policy", description="Recently increased coverage.", type="Document"),
        ],
        defense_evidence=[
            Evidence(id="D-1", title="Alibi", description="Defendant was elsewhere.", type="Testimony"),
            Evidence(id="D-2", title="Character Reference", description="No history of arson.", type="Testimony"),
            Evidence(id="D-3", title="Security Footage", description="Shows someone else nearby.", type="Document"),
        ],
    )
    prosecutor_response = TurnOutput(text="The defendant had a clear motive.", attached_evidence_ids=["P-1"])
    defense_response = TurnOutput(text="My client has a solid alibi.", attached_evidence_ids=["D-1"])
    judge_response = Verdict(
        guilty=True, reasoning="The prosecution's evidence was more convincing overall.", defense_score=4, prosecution_score=8
    )

    monkeypatch.setattr(ai_clerk_module, "get_llm", lambda temperature=0.0: _FakeLLM(case_file_response))
    monkeypatch.setattr(prosecutor_module, "get_llm", lambda temperature=0.0: _FakeLLM(prosecutor_response))
    monkeypatch.setattr(defense_module, "get_llm", lambda temperature=0.0: _FakeLLM(defense_response))
    monkeypatch.setattr(ai_judge_module, "get_llm", lambda temperature=0.0: _FakeLLM(judge_response))

    return create_workflow()


class TestWorkflowIntegration:
    def test_runs_the_full_debate_and_terminates_at_the_judge(self, wired_workflow):
        final_state = wired_workflow.invoke({"user_prompt": "A warehouse fire.", "allow_evidence_reuse": False})

        speakers = [message.speaker for message in final_state["messages"]]
        assert speakers == ["Prosecutor", "Defense"] * 3 + ["Judge"]
        assert final_state["messages"][-1].text.startswith("VERDICT: GUILTY")
        assert final_state["system_events"] == []  # no fallback/retry path was ever hit

    def test_evidence_is_consumed_across_rounds_without_reuse(self, wired_workflow):
        final_state = wired_workflow.invoke({"user_prompt": "A warehouse fire.", "allow_evidence_reuse": False})

        # Round 1 attaches P-1/D-1; rounds 2-3 ask for the same IDs again, but
        # validate_turn_output filters them out once they're marked used.
        prosecutor_messages = [final_state["messages"][i] for i in (0, 2, 4)]
        defense_messages = [final_state["messages"][i] for i in (1, 3, 5)]

        assert prosecutor_messages[0].attached_evidence_ids == ["P-1"]
        assert all(message.attached_evidence_ids == [] for message in prosecutor_messages[1:])

        assert defense_messages[0].attached_evidence_ids == ["D-1"]
        assert all(message.attached_evidence_ids == [] for message in defense_messages[1:])

        prosecution_by_id = {e.id: e for e in final_state["prosecution_evidence"]}
        defense_by_id = {e.id: e for e in final_state["defense_evidence"]}
        assert prosecution_by_id["P-1"].is_used is True
        assert defense_by_id["D-1"].is_used is True

    def test_case_summary_from_the_clerk_is_threaded_through_to_the_end(self, wired_workflow):
        final_state = wired_workflow.invoke({"user_prompt": "A warehouse fire.", "allow_evidence_reuse": False})

        assert final_state["case_summary"].crime == "Arson"
