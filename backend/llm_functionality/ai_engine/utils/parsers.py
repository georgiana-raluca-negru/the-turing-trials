import re
from typing import Type, TypeVar

from json_repair import repair_json
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, ValidationError

T = TypeVar('T', bound=BaseModel)


def strip_reasoning_blocks(text: str) -> str:
    return re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL | re.IGNORECASE).strip()


def extract_json_candidate(text: str) -> str:
    json_match = re.search(r'```(?:json)?\s*(.*?)\s*```', text, flags=re.DOTALL | re.IGNORECASE)
    if json_match:
        return json_match.group(1)

    first_object = _extract_bracketed_payload(text, '{', '}')
    if first_object:
        return first_object

    first_array = _extract_bracketed_payload(text, '[', ']')
    if first_array:
        return first_array

    return text


def _extract_bracketed_payload(text: str, opener: str, closer: str) -> str | None:
    start_index = text.find(opener)
    end_index = text.rfind(closer)
    if start_index == -1 or end_index == -1 or end_index <= start_index:
        return None
    return text[start_index:end_index + 1]


def unwrap_payload(payload):
    current_payload = payload

    while isinstance(current_payload, list) and len(current_payload) == 1:
        current_payload = current_payload[0]

    while isinstance(current_payload, dict):
        nested_payload = None
        for key in ("result", "response", "output", "data", "argument", "verdict", "case_file"):
            value = current_payload.get(key)
            if isinstance(value, (dict, list)):
                nested_payload = value
                break

        if nested_payload is None:
            break

        current_payload = nested_payload
        while isinstance(current_payload, list) and len(current_payload) == 1:
            current_payload = current_payload[0]

    return current_payload


def safe_preview(text: str, limit: int = 600) -> str:
    preview = text[:limit]
    return preview.encode("ascii", "backslashreplace").decode("ascii")

_SCHEMA_META_KEYS = frozenset({
    "$defs", "$schema", "$id", "$ref",
    "additionalProperties", "allOf", "anyOf", "oneOf",
    "definitions", "properties", "required", "title", "type",
    "description",
})


def _strip_schema_meta(data: dict) -> dict:
    """Remove JSON Schema structural keys that an LLM may accidentally include."""
    return {k: v for k, v in data.items() if k not in _SCHEMA_META_KEYS}


def clean_and_parse_json(text: str, model_class: Type[T]) -> T:
    """
    Robust JSON parser specifically designed to handle LLM output issues.
    It cleans up reasoning blocks (<think>), extracts JSON snippets from Markdown,
    and aggressively repairs malformed JSON (missing quotes, trailing commas, unescaped characters).
    """

    text_cleaned = strip_reasoning_blocks(text)
    json_str = extract_json_candidate(text_cleaned)

    try:
        repaired_data = repair_json(json_str, return_objects=True)
        repaired_data = unwrap_payload(repaired_data)

        if repaired_data in (None, "", [], {}):
            raise ValueError("Repaired JSON is empty or invalid.")

        # Direct validation
        if not isinstance(repaired_data, dict):
            return model_class.model_validate(repaired_data)

        try:
            return model_class.model_validate(repaired_data)
        except ValidationError:
            # MiniMax sometimes returns the JSON schema definition merged with the
            # actual data in one object. Strip schema meta-keys and retry.
            stripped = _strip_schema_meta(repaired_data)
            if stripped and stripped != repaired_data:
                return model_class.model_validate(stripped)
            raise

    except (ValueError, TypeError, ValidationError) as e:
        print(f"\n[PARSER WARNING] Primary parsing/repair failed: {e}\nFalling back to Pydantic Output Parser...")

        parser = PydanticOutputParser(pydantic_object=model_class)
        try:
            parsed = parser.invoke(text_cleaned)
            if isinstance(parsed, BaseModel):
                return model_class.model_validate(parsed.model_dump())
            return model_class.model_validate(parsed)
        except Exception as e_fallback:
            preview = safe_preview(text)
            print(f"\n[PARSER ERROR] Fatal parsing failure. Preview:\n{preview}\n")
            raise e_fallback
