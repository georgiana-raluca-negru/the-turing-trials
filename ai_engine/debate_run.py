import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ai_engine.graph.workflow import create_workflow

def run_debate_streaming():
    output_file = "run_test_output.txt"
    app = create_workflow()
    
    initial_state = {
        "user_prompt": "Un jaf la un muzeu de arta. Furtul unui tablou celebru folosind gaz lacrimogen si o replica perfecta a tabloului."
    }
    
    print(f"Setting up full MVP workflow. Writing stream to {output_file}...")
    
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("================ THE TURING TRIALS MVP =================\n")
        f.write(f"PROMPT: {initial_state['user_prompt']}\n")
        f.write("========================================================\n\n")
        
    print("Invoking Multi-Agent Debate in Streaming Mode...")
    
    current_round = 1
    
    try:
        for output in app.stream(initial_state):
            for node_name, state_update in output.items():
                
                with open(output_file, "a", encoding="utf-8") as f:
                    print(f"--- Node '{node_name}' finished executing ---")
                    
                    if node_name == "ai_clerk":
                        f.write("================ CASE SUMMARY ================\n")
                        f.write(f"CRIME: {state_update['case_summary'].crime}\n")
                        f.write(f"CHARGES: {', '.join(state_update['case_summary'].charges)}\n")
                        f.write(f"BACKGROUND STORY: \n{state_update['case_summary'].background_story}\n\n")
                        
                        f.write("================ EVIDENCE GENERATED ================\n")
                        f.write("--- PROSECUTION EVIDENCE ---\n")
                        for ev in state_update['prosecution_evidence']:
                            f.write(f"[{ev.id}] {ev.title} ({ev.type}): {ev.description}\n")
                            
                        f.write("\n--- DEFENSE EVIDENCE ---\n")
                        for ev in state_update['defense_evidence']:
                            f.write(f"[{ev.id}] {ev.title} ({ev.type}): {ev.description}\n")
                            
                        f.write("\n================ DEBATE START ================\n")
                        current_round = 1
                        
                    elif node_name in ["prosecutor", "defense", "ai_judge"]:
                        latest_msg = state_update['messages'][-1]
                        
                        if latest_msg.speaker == "Judge":
                            f.write(f"\n>>>> {latest_msg.speaker.upper()} <<<<\n")
                            f.write(f"{latest_msg.text}\n")
                        else:
                            f.write(f"\n[{latest_msg.speaker.upper()}] (Round {current_round})\n")
                            f.write(f"{latest_msg.text}\n")
                            if latest_msg.attached_evidence_ids:
                                f.write(f"   * Attached Evidence: {latest_msg.attached_evidence_ids}\n")
                            f.write("-" * 60 + "\n")
                            
                        # Increment round after defense's turn is fully logged
                        if node_name == "defense":
                            current_round += 1
                            
    except Exception as e:
        print(f"An error occurred during streaming: {e}")
        with open(output_file, "a", encoding="utf-8") as f:
            f.write(f"\n[ERROR]: {e}\n")

if __name__ == "__main__":
    run_debate_streaming()