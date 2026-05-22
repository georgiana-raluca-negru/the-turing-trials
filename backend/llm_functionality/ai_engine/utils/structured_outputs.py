from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable, Generic, Iterable, TypeVar

from langchain_core.messages import BaseMessage
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel

from ai_engine.models.schemas import Argument, CaseFile, TurnOutput, Verdict
from ai_engine.utils.parsers import clean_and_parse_json

T = TypeVar("T", bound=BaseModel)


class StructuredOutputError(RuntimeError):
    """Raised when a model fails to produce valid structured output after retries."""


class SemanticValidationError(StructuredOutputError):
    """Raised when structured output parses but violates semantic constraints."""


@dataclass
class StructuredGenerationResult(Generic[T]):
    value: T
    strategy: str
    raw_text: str | None


def generate_structured_response(
    *,
    llm,
    prompt,
    variables: dict[str, Any],
    schema: type[T],
    role_name: str,
    validator: Callable[[T], T] | None = None,
    transport_retries: int = 2,
) -> StructuredGenerationResult[T]:
    parser = PydanticOutputParser(pydantic_object=schema)
    strategies = (
        ("json_schema", "Return a response that matches the requested schema exactly. Do not wrap it in markdown."),
        ("function_calling", "Return a response that matches the requested schema exactly. Do not add extra prose."),
        ("json_mode", "Return a response that matches the requested schema exactly. Do not add extra prose."),
        ("manual_parser", parser.get_format_instructions()),
    )

    last_error: Exception | None = None
    failure_notes: list[str] = []

    for strategy_name, response_contract in strategies:
        attempt_number = 0
        while attempt_number < transport_retries:
            attempt_number += 1
            raw_text = None

            try:
                payload = dict(variables)
                payload["response_contract"] = response_contract

                if strategy_name == "manual_parser":
                    raw_response = (prompt | llm).invoke(payload)
                    raw_text = message_to_text(raw_response)
                    value = clean_and_parse_json(raw_text, schema)
                else:
                    structured_llm = llm.with_structured_output(
                        schema,
                        method=strategy_name,
                        include_raw=True,
                    )
                    structured_response = (prompt | structured_llm).invoke(payload)
                    value, raw_text = coerce_structured_response(structured_response, schema)

                if validator is not None:
                    value = validator(value)

                return StructuredGenerationResult(
                    value=value,
                    strategy=strategy_name,
                    raw_text=raw_text,
                )

            except Exception as exc:
                last_error = exc
                failure_notes.append(f"{strategy_name}/attempt{attempt_number}: {exc}")
                if is_transient_llm_error(exc) and attempt_number < transport_retries:
                    print(f"[LLM WARNING] {role_name} hit a transient error via {strategy_name}: {exc}. Retrying...")
                    time.sleep(min(2 ** attempt_number, 4))
                    continue
                break

    failure_summary = " | ".join(failure_notes[-8:]) if failure_notes else "No attempts were recorded."
    raise StructuredOutputError(
        f"{role_name} failed to produce valid structured output after retries. {failure_summary}"
    ) from last_error


def coerce_structured_response(response: Any, schema: type[T]) -> tuple[T, str | None]:
    parsed_payload = response
    raw_text = None
    parsing_error = None

    if isinstance(response, dict) and (
        "parsed" in response or "raw" in response or "parsing_error" in response
    ):
        parsed_payload = response.get("parsed")
        raw_text = message_to_text(response.get("raw"))
        parsing_error = response.get("parsing_error")

    if parsing_error is not None:
        if raw_text:
            try:
                return clean_and_parse_json(raw_text, schema), raw_text
            except Exception:
                pass
        raise parsing_error

    if parsed_payload is None:
        if raw_text:
            return clean_and_parse_json(raw_text, schema), raw_text
        raise StructuredOutputError("Structured response did not contain a parsed payload.")

    if isinstance(parsed_payload, schema):
        return parsed_payload, raw_text

    if isinstance(parsed_payload, BaseModel):
        return schema.model_validate(parsed_payload.model_dump()), raw_text

    return schema.model_validate(parsed_payload), raw_text


def message_to_text(message: Any) -> str | None:
    if message is None:
        return None

    content = message.content if isinstance(message, BaseMessage) else getattr(message, "content", message)

    if isinstance(content, str):
        return content

    if isinstance(content, list):
        text_parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                text_parts.append(item)
                continue

            if isinstance(item, dict):
                item_text = item.get("text") or item.get("content")
                if item_text:
                    text_parts.append(str(item_text))
                    continue

            text_parts.append(str(item))
        return "\n".join(part for part in text_parts if part).strip()

    return str(content)


def is_transient_llm_error(exc: Exception) -> bool:
    error_text = str(exc).lower()
    return any(
        marker in error_text
        for marker in (
            "connection error",
            "timed out",
            "timeout",
            "temporarily unavailable",
            "rate limit",
            "429",
            "502",
            "503",
            "504",
        )
    )


def render_history(messages: list[Argument]) -> str:
    if not messages:
        return "The trial has just begun."

    return "\n".join(
        f"{message.speaker}: {message.text} (Ev:{message.attached_evidence_ids})"
        for message in messages
    )


def mark_evidence_used(evidence_list, used_ids: Iterable[str]):
    used_lookup = set(used_ids)
    new_evidence_list = []
    for evidence in evidence_list:
        updated_evidence = evidence.model_copy(update={"is_used": evidence.is_used or evidence.id in used_lookup})
        new_evidence_list.append(updated_evidence)
    return new_evidence_list


def validate_case_file(case_file: CaseFile, *, min_evidence_per_side: int = 3) -> CaseFile:
    errors: list[str] = []

    if len(case_file.prosecution_evidence) < min_evidence_per_side:
        errors.append(
            f"Expected at least {min_evidence_per_side} prosecution evidence items, got {len(case_file.prosecution_evidence)}."
        )
    if len(case_file.defense_evidence) < min_evidence_per_side:
        errors.append(
            f"Expected at least {min_evidence_per_side} defense evidence items, got {len(case_file.defense_evidence)}."
        )

    errors.extend(_validate_unique_evidence_ids(case_file.prosecution_evidence, "prosecution"))
    errors.extend(_validate_unique_evidence_ids(case_file.defense_evidence, "defense"))

    prosecution_ids = {evidence.id for evidence in case_file.prosecution_evidence}
    defense_ids = {evidence.id for evidence in case_file.defense_evidence}
    overlapping_ids = sorted(prosecution_ids & defense_ids)
    if overlapping_ids:
        errors.append(f"Evidence IDs must be unique across both sides. Overlaps: {overlapping_ids}")

    if errors:
        raise SemanticValidationError("; ".join(errors))

    return case_file


def validate_turn_output(turn_output: TurnOutput, *, available_evidence_ids: Iterable[str]) -> TurnOutput:
    normalized_ids = []
    seen_ids = set()
    for evidence_id in turn_output.attached_evidence_ids:
        if evidence_id not in seen_ids:
            normalized_ids.append(evidence_id)
            seen_ids.add(evidence_id)

    allowed_ids = set(available_evidence_ids)
    valid_ids = [evidence_id for evidence_id in normalized_ids if evidence_id in allowed_ids]
    if len(valid_ids) > 2:
        valid_ids = valid_ids[:2]

    return turn_output.model_copy(
        update={
            "text": turn_output.text.strip(),
            "attached_evidence_ids": valid_ids,
        }
    )


def validate_verdict(verdict: Verdict) -> Verdict:
    reasoning = verdict.reasoning.strip()
    if not reasoning:
        raise SemanticValidationError("Verdict reasoning cannot be empty.")
    return verdict.model_copy(update={"reasoning": reasoning})


def build_missed_turn_argument(speaker: str, reason: str) -> tuple[Argument, str]:
    warning = (
        f"{speaker} missed the turn after structured parsing retries failed. "
        f"Continuing the debate without new evidence. Last error: {reason}"
    )
    argument = Argument(
        speaker=speaker,
        text=(
            f"[TURN MISSED] {speaker} failed to produce a valid structured argument after retries. "
            "The debate continues without new evidence for this side."
        ),
        attached_evidence_ids=[],
    )
    return argument, warning


def build_judge_fallback_argument(reason: str) -> tuple[Argument, str]:
    warning = (
        "Judge verdict generation failed after structured parsing retries. "
        f"Manual review is required. Last error: {reason}"
    )
    argument = Argument(
        speaker="Judge",
        text=(
            "VERDICT UNAVAILABLE\n"
            "Reasoning: The judge failed to return a valid structured verdict after retries. "
            "The debate transcript remains available for manual review."
        ),
        attached_evidence_ids=[],
    )
    return argument, warning


def _validate_unique_evidence_ids(evidence_list, side_name: str) -> list[str]:
    errors: list[str] = []
    seen_ids = set()
    duplicate_ids = set()

    for evidence in evidence_list:
        if evidence.id in seen_ids:
            duplicate_ids.add(evidence.id)
        seen_ids.add(evidence.id)

    if duplicate_ids:
        errors.append(f"{side_name.capitalize()} evidence contains duplicate IDs: {sorted(duplicate_ids)}")

    return errors
