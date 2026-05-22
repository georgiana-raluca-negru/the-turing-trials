import os
import sys

# Adaugam radacina proiectului in sys.path pentru a putea importa modulele `ai_engine`
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ai_engine.graph.workflow import create_workflow


def configure_utf8_stdio():
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="backslashreplace")


def env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def test_clerk():
    configure_utf8_stdio()
    print("Setting up workflow...")
    app = create_workflow()
    allow_evidence_reuse = env_flag("ALLOW_EVIDENCE_REUSE", default=False)

    initial_state = {
        "user_prompt": "Un caz de furt de identitate informaticÄƒ unde acuzatul susÈ›ine cÄƒ laptopul i-a fost controlat de la distanÈ›Äƒ.",
        "allow_evidence_reuse": allow_evidence_reuse,
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
