import json
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from ai_engine.state.match_state import MatchState
from ai_engine.config.llm_config import get_llm
from ai_engine.models.schemas import Argument
from ai_engine.utils.parsers import clean_and_parse_json

def defense_turn_node(state: MatchState) -> dict:
    llm = get_llm(temperature=0.7)
    parser = PydanticOutputParser(pydantic_object=Argument)
    
    case_summary = state["case_summary"].model_dump_json()
    available_evidence = [e.model_dump() for e in state["defense_evidence"] if not e.is_used]
    history = "\n".join([f"{msg.speaker}: {msg.text} (Ev:{msg.attached_evidence_ids})" for msg in state["messages"]])
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are the Defense Attorney in a courtroom trial. Your goal is to prove your client is not guilty and dismantle the prosecutor's case.\n"
                   "You MUST base your arguments ONLY on the available evidence provided below. "
                   "DO NOT invent new evidence. You may attach up to 2 evidence items to your argument using their IDs.\n\n"
                   "Case Context:\n{case_summary}\n\n"
                   "Your Available Evidence:\n{evidence}\n\n"
                   "IMPORTANT: Output ONLY valid JSON. You MUST properly escape all quotes inside string values to prevent JSON parsing errors.\n"
                   "{format_instructions}"),
        ("human", "Here is the trial history so far:\n{history}\n\nMake your next argument.")
    ])
    
    chain = prompt | llm
    raw_response = chain.invoke({
        "case_summary": case_summary,
        "evidence": json.dumps(available_evidence, indent=2),
        "history": history if history else "The trial has just begun.",
        "format_instructions": parser.get_format_instructions()
    })
    
    argument = clean_and_parse_json(raw_response.content, Argument)
    argument.speaker = "Defense"
    
    used_ids = argument.attached_evidence_ids
    new_evidence_list = []
    for ev in state["defense_evidence"]:
        if ev.id in used_ids:
            ev.is_used = True
        new_evidence_list.append(ev)
        
    messages = state["messages"] + [argument]
    
    return {
        "messages": messages,
        "defense_evidence": new_evidence_list,
        "round_number": state.get("round_number", 1) + 1 # Increment round after defense
    }