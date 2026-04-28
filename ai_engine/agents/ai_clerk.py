from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from ai_engine.state.match_state import MatchState
from ai_engine.config.llm_config import get_llm
from ai_engine.models.schemas import CaseFile
from ai_engine.utils.parsers import clean_and_parse_json

def generate_case_node(state: MatchState) -> dict:
    """
    LangGraph node to generate the case summary and evidence inventory based on user prompt.
    """
    user_prompt = state.get("user_prompt", "")
    
    llm = get_llm(temperature=0.1)
    parser = PydanticOutputParser(pydantic_object=CaseFile)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are the AI Clerk in a courtroom simulation. Your job is to take a short prompt from the user "
                   "and generate a complete case file including the case summary (crime, charges, background story) "
                   "and a balanced inventory of evidence for both the defense and prosecution. "
                   "Ensure the evidence is creative, relevant, and provides strong arguments for both sides.\n\n"
                   "IMPORTANT: Output ONLY valid JSON. You MUST properly escape all quotes inside string values to prevent JSON parsing errors.\n"
                   "{format_instructions}"),
        ("human", "Generate a case based on this prompt: {prompt}")
    ])
    
    chain = prompt | llm
    
    raw_response = chain.invoke({
        "prompt": user_prompt,
        "format_instructions": parser.get_format_instructions()
    })
    
    response = clean_and_parse_json(raw_response.content, CaseFile)
    
    return {
        "case_summary": response.case_summary,
        "defense_evidence": response.defense_evidence,
        "prosecution_evidence": response.prosecution_evidence,
        "messages": [],
        "round_number": 1
    }