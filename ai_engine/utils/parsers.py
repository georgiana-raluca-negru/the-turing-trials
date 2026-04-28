import re
import json
from json_repair import repair_json
from typing import Type, TypeVar
from pydantic import BaseModel, ValidationError
from langchain_core.output_parsers import PydanticOutputParser

T = TypeVar('T', bound=BaseModel)

def clean_and_parse_json(text: str, model_class: Type[T]) -> T:
    """
    Robust JSON parser specifically designed to handle LLM output issues.
    It cleans up reasoning blocks (<think>), extracts JSON snippets from Markdown,
    and aggressively repairs malformed JSON (missing quotes, trailing commas, unescaped characters).
    """
    
    # 1. Strip reasoning blocks (like Minimax's <think> tags)
    text_cleaned = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL | re.IGNORECASE).strip()
    
    # 2. Extract JSON from Markdown blocks if present
    json_match = re.search(r'```(?:json)?\s*(.*?)\s*```', text_cleaned, flags=re.DOTALL | re.IGNORECASE)
    if json_match:
        json_str = json_match.group(1)
    else:
        json_str = text_cleaned
        
    try:
        # 3. Aggressive JSON repair (fixes unescaped quotes, missing brackets, trailing commas)
        # return_objects=True parses it directly into a Python dict/list
        repaired_data = repair_json(json_str, return_objects=True)
        
        if not repaired_data:
            raise ValueError("Repaired JSON is empty or invalid.")
            
        if isinstance(repaired_data, list):
            # Sometimes the LLM wraps the response in a JSON array like [{...}]
            repaired_data = repaired_data[0]
            
        # 4. Instantiate the Pydantic model with the repaired dictionary
        return model_class(**repaired_data)
        
    except (ValueError, TypeError, ValidationError) as e:
        print(f"\n[PARSER WARNING] Primary parsing/repair failed: {e}\nFalling back to Pydantic Output Parser...")
        
        # 5. Last resort fallback to Langchain's Pydantic parser logic
        parser = PydanticOutputParser(pydantic_object=model_class)
        try:
            return parser.invoke(text_cleaned)
        except Exception as e_fallback:
            print(f"\n[PARSER ERROR] Fatal parsing failure. Original text:\n{text}\n")
            raise e_fallback
