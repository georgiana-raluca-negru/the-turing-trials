from langgraph.graph import StateGraph, END
from ai_engine.state.match_state import MatchState
from ai_engine.agents.ai_clerk import generate_case_node
from ai_engine.agents.prosecutor import prosecutor_turn_node
from ai_engine.agents.defense import defense_turn_node
from ai_engine.agents.ai_judge import judge_verdict_node

def should_continue_debate(state: MatchState) -> str:
    """Check if we have reached the max number of rounds."""
    if state.get("round_number", 1) > 3:
        return "ai_judge"
    return "prosecutor"

def create_workflow():
    # Initialize the state graph
    workflow = StateGraph(MatchState)
    
    # Add nodes
    workflow.add_node("ai_clerk", generate_case_node)
    workflow.add_node("prosecutor", prosecutor_turn_node)
    workflow.add_node("defense", defense_turn_node)
    workflow.add_node("ai_judge", judge_verdict_node)
    
    # Define edges
    workflow.set_entry_point("ai_clerk")
    
    workflow.add_edge("ai_clerk", "prosecutor")
    workflow.add_edge("prosecutor", "defense")
    
    # Conditional routing after defense turn
    workflow.add_conditional_edges(
        "defense",
        should_continue_debate,
        {
            "prosecutor": "prosecutor",
            "ai_judge": "ai_judge"
        }
    )
    
    workflow.add_edge("ai_judge", END)
    
    # Compile
    app = workflow.compile()
    
    return app

# Global instance exposed for LangGraph Studio / LangGraph CLI
app = create_workflow()