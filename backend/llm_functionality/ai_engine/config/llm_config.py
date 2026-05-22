import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.language_models.chat_models import BaseChatModel

load_dotenv()

def get_llm(temperature: float = 0.0) -> BaseChatModel:
    """
    Returns the configured LLM using Minimax (via OpenAI compatible endpoint), 
    as configured in the .env file.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.minimax.io/v1")
    model_name = os.getenv("DEFAULT_MODEL_NAME", "MiniMax-Text-01")
    
    if not api_key:
        raise ValueError("OPENAI_API_KEY (for Minimax) not found in environment variables.")
        
    return ChatOpenAI(
        api_key=api_key,
        base_url=base_url,
        model=model_name,
        temperature=temperature,
        max_tokens=4096,
        timeout=90,
        max_retries=2,
    )
