from langchain_core.prompts import ChatPromptTemplate

from ai_engine.state.match_state import MatchState
from ai_engine.config.llm_config import get_llm
from ai_engine.models.schemas import Verdict, Argument
from ai_engine.utils.structured_outputs import (
    build_judge_fallback_argument,
    generate_structured_response,
    render_history,
    validate_verdict,
)
from legal_grounding.citations import (
    legal_citation_instructions,
    render_legal_context,
    validate_and_clean_citations,
)
from legal_grounding.models import LegalContext

def judge_verdict_node(state: MatchState) -> dict:
    llm = get_llm(temperature=0.3)
    
    case_summary = state["case_summary"].model_dump_json(indent=2)
    history = render_history(state["messages"])
    legal_context = state.get("legal_context", LegalContext())
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are the AI Judge in a courtroom trial. The debate has concluded.\n"
                   "Review the case context and the full debate history.\n"
                   "Provide a motivated final verdict, declaring if the defendant is guilty or not, "
                   "and score both the prosecution and defense out of 10 based on logic, use of evidence, "
                   "and persuasiveness. Ground every conclusion about Romanian law only in the official legislative "
                   "excerpts supplied below. Keep the reasoning under 250 words.\n\n"
                   "Case Context:\n{case_summary}\n\n"
                   "Official Romanian Legislation:\n{legal_context}\n\n"
                   "Citation rules:\n{citation_rules}\n\n"
                   "{response_contract}"),
        ("human", "Here is the full trial history:\n{history}\n\nProvide your final verdict.")
    ])

    system_events = list(state.get("system_events", []))
    try:
        result = generate_structured_response(
            llm=llm,
            prompt=prompt,
            variables={
                "case_summary": case_summary,
                "history": history,
                "legal_context": render_legal_context(legal_context),
                "citation_rules": legal_citation_instructions(),
            },
            schema=Verdict,
            role_name="Judge",
            validator=validate_verdict,
        )
        print(f"[LLM INFO] Judge response accepted via {result.strategy}.")
        verdict = result.value
        citation_result = validate_and_clean_citations(verdict.reasoning, legal_context.sources)
        if citation_result.invalid_ids:
            warning = f"Judge used invalid legal citation IDs: {citation_result.invalid_ids}. Markers were removed."
            system_events.append(warning)

        verdict_text = (
            f"VERDICT: {'GUILTY' if verdict.guilty else 'NOT GUILTY'}\n"
            f"Reasoning: {citation_result.text}\n"
            f"Scores - Prosecution: {verdict.prosecution_score}/10, Defense: {verdict.defense_score}/10"
        )
        judge_arg = Argument(
            speaker="Judge",
            text=verdict_text,
            attached_evidence_ids=[],
            legal_citation_ids=citation_result.cited_ids,
        )
    except Exception as exc:
        judge_arg, warning = build_judge_fallback_argument(str(exc))
        system_events.append(warning)
        print(f"[TURN WARNING] {warning}")

    return {
        "messages": state["messages"] + [judge_arg],
        "system_events": system_events,
    }
