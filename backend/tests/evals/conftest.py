from dotenv import load_dotenv

# Eval tests call the real MiniMax LLM through the agent nodes, which need
# OPENAI_API_KEY from the repo-root .env (the unit-test suite never reaches
# code that requires it, so tests/conftest.py doesn't load it).
load_dotenv()
