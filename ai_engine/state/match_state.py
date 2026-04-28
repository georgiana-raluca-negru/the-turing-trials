from typing import TypedDict, List
from ai_engine.models.schemas import Evidence, CaseContext, Argument

class MatchState(TypedDict):
    user_prompt: str
    case_summary: CaseContext
    defense_evidence: List[Evidence]
    prosecution_evidence: List[Evidence]
    messages: List[Argument] # Chat history
    round_number: int # Current round number