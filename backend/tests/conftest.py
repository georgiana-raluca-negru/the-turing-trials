import os
import sys

# `ai_engine` and `backend_integration` live outside the `backend/app` package
# root, under `llm_functionality/`. The running server gets this on PYTHONPATH
# via the Dockerfile; tests need the same path added manually.
_LLM_FUNCTIONALITY_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "llm_functionality")
)
if _LLM_FUNCTIONALITY_DIR not in sys.path:
    sys.path.insert(0, _LLM_FUNCTIONALITY_DIR)
