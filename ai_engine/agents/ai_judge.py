import json
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from ai_engine.state.match_state import MatchState
from ai_engine.config.llm_config import get_llm
from ai_engine.models.schemas import Verdict, Argument
from ai_engine.utils.parsers import clean_and_parse_json

def judge_verdict_node(state: MatchState) -> dict:
    llm = get_llm(temperature=0.3)
    parser = PydanticOutputParser(pydantic_object=Verdict)
    
    case_summary = state["case_summary"].model_dump_json()
    history = "\n".join([f"{msg.speaker}: {msg.text} (Ev:{msg.attached_evidence_ids})" for msg in state["messages"]])
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are the AI Judge in a courtroom trial. The debate has concluded.\n"
                   "Review the case context and the full debate history.\n"
                   "Provide a motivated final verdict, declaring if the defendant is guilty or not, "
                   "and score both the prosecution and defense out of 10 based on logic, use of evidence, "
                   "and persuasiveness.\n\n"
                   "Case Context:\n{case_summary}\n\n"
                   "IMPORTANT: Output ONLY valid JSON. You MUST properly escape all quotes inside string values to prevent JSON parsing errors.\n"
                   "{format_instructions}"),
        ("human", "Here is the full trial history:\n{history}\n\nProvide your final verdict.")
    ])
    
    chain = prompt | llm
    raw_response = chain.invoke({
        "case_summary": case_summary,
        "history": history,
        "format_instructions": parser.get_format_instructions()
    })
    
    verdict = clean_and_parse_json(raw_response.content, Verdict)
    
    verdict_text = f"VERDICT: {'GUILTY' if verdict.guilty else 'NOT GUILTY'}\nReasoning: {verdict.reasoning}\nScores - Prosecution: {verdict.prosecution_score}/10, Defense: {verdict.defense_score}/10"
    
    judge_arg = Argument(speaker="Judge", text=verdict_text, attached_evidence_ids=[])
    
    return {
        "messages": state["messages"] + [judge_arg]
    }