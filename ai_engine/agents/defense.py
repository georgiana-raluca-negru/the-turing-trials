import json
from langchain_core.prompts import ChatPromptTemplate

from ai_engine.state.match_state import MatchState
from ai_engine.config.llm_config import get_llm
from ai_engine.models.schemas import Argument, TurnOutput
from ai_engine.utils.structured_outputs import (
    build_missed_turn_argument,
    generate_structured_response,
    mark_evidence_used,
    render_history,
    validate_turn_output,
)

def defense_turn_node(state: MatchState) -> dict:
    llm = get_llm(temperature=0.7)
    allow_evidence_reuse = state.get("allow_evidence_reuse", False)
    
    case_summary = state["case_summary"].model_dump_json(indent=2)
    available_evidence = [
        e.model_dump() for e in state["defense_evidence"]
        if allow_evidence_reuse or not e.is_used
    ]
    available_evidence_ids = [evidence["id"] for evidence in available_evidence]
    history = render_history(state["messages"])
    evidence_rule = (
        "No attachable evidence items remain. You may still argue from the debate history, "
        "but attached_evidence_ids MUST be []."
        if not available_evidence_ids
        else (
            f"Evidence reuse is enabled. You may attach only these evidence IDs, including ones used earlier: {available_evidence_ids}."
            if allow_evidence_reuse
            else f"You may attach only these remaining evidence IDs: {available_evidence_ids}."
        )
    )
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are the Defense Attorney in a courtroom trial. Your goal is to prove your client is not guilty and dismantle the prosecutor's case.\n"
                   "You MUST base your arguments ONLY on the available evidence provided below. "
                   "DO NOT invent new evidence. You may attach 0 to 2 evidence items to your argument using their IDs.\n"
                   "{evidence_rule}\n"
                   "Keep the argument concise, specific, and under 220 words.\n\n"
                   "Case Context:\n{case_summary}\n\n"
                   "Your Available Evidence:\n{evidence}\n\n"
                   "{response_contract}"),
        ("human", "Here is the trial history so far:\n{history}\n\nMake your next argument.")
    ])

    system_events = list(state.get("system_events", []))
    try:
        result = generate_structured_response(
            llm=llm,
            prompt=prompt,
            variables={
                "case_summary": case_summary,
                "evidence": json.dumps(available_evidence, indent=2, ensure_ascii=False),
                "evidence_rule": evidence_rule,
                "history": history,
            },
            schema=TurnOutput,
            role_name="Defense",
            validator=lambda turn: validate_turn_output(turn, available_evidence_ids=available_evidence_ids),
        )
        print(f"[LLM INFO] Defense response accepted via {result.strategy}.")
        turn_output = result.value
        argument = Argument(
            speaker="Defense",
            text=turn_output.text,
            attached_evidence_ids=turn_output.attached_evidence_ids,
        )
    except Exception as exc:
        argument, warning = build_missed_turn_argument("Defense", str(exc))
        system_events.append(warning)
        print(f"[TURN WARNING] {warning}")

    new_evidence_list = mark_evidence_used(state["defense_evidence"], argument.attached_evidence_ids)
    messages = state["messages"] + [argument]
    
    return {
        "allow_evidence_reuse": allow_evidence_reuse,
        "messages": messages,
        "defense_evidence": new_evidence_list,
        "round_number": state.get("round_number", 1) + 1, # Increment round after defense
        "system_events": system_events,
    }
