from langchain_core.prompts import ChatPromptTemplate

from ai_engine.state.match_state import MatchState
from ai_engine.config.llm_config import get_llm
from ai_engine.models.schemas import CaseFile
from ai_engine.utils.structured_outputs import generate_structured_response, validate_case_file

def generate_case_node(state: MatchState) -> dict:
    """
    LangGraph node to generate the case summary and evidence inventory based on user prompt.
    """
    user_prompt = state.get("user_prompt", "")
    
    llm = get_llm(temperature=0.1)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are the AI Clerk in a courtroom simulation. Your job is to take a short prompt from the user "
                   "and generate a complete case file including the case summary (crime, charges, background story) "
                   "and a balanced inventory of evidence for both the defense and prosecution. "
                   "Generate exactly 4 evidence items for the prosecution and exactly 4 evidence items for the defense. "
                   "Ensure the evidence is creative, relevant, and provides strong arguments for both sides. "
                   "Keep evidence descriptions concise but specific.\n\n"
                   "{response_contract}"),
        ("human", "Generate a case based on this prompt: {prompt}")
    ])
    
    result = generate_structured_response(
        llm=llm,
        prompt=prompt,
        variables={"prompt": user_prompt},
        schema=CaseFile,
        role_name="AI Clerk",
        validator=validate_case_file,
    )
    print(f"[LLM INFO] AI Clerk response accepted via {result.strategy}.")
    response = result.value
    
    return {
        "allow_evidence_reuse": state.get("allow_evidence_reuse", False),
        "case_summary": response.case_summary,
        "defense_evidence": response.defense_evidence,
        "prosecution_evidence": response.prosecution_evidence,
        "messages": [],
        "round_number": 1,
        "system_events": []
    }
