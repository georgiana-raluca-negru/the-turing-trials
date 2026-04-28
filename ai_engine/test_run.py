import sys
import os

# Adaugam radacina proiectului in sys.path pentru a putea importa modulele `ai_engine`
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ai_engine.graph.workflow import create_workflow

def test_clerk():
    print("Setting up workflow...")
    app = create_workflow()
    
    initial_state = {
        "user_prompt": "Un caz de furt de identitate informatică unde acuzatul susține că laptopul i-a fost controlat de la distanță."
    }
    
    print("Invoking AI Clerk... Please wait. (Aceasta operatiune va apela LLM-ul)")
    try:
        final_state = app.invoke(initial_state)
        
        print("\n--- CASE SUMMARY ---")
        print(f"Crime: {final_state['case_summary'].crime}")
        print(f"Charges: {final_state['case_summary'].charges}")
        print(f"Background: {final_state['case_summary'].background_story}")
        
        print("\n--- PROSECUTION EVIDENCE ---")
        for ev in final_state['prosecution_evidence']:
            print(f"- [{ev.id}] {ev.title} ({ev.type}): {ev.description}")
            
        print("\n--- DEFENSE EVIDENCE ---")
        for ev in final_state['defense_evidence']:
            print(f"- [{ev.id}] {ev.title} ({ev.type}): {ev.description}")
            
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    test_clerk()