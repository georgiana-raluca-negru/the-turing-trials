from __future__ import annotations

import json
import os
from typing import Any, TypedDict

from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import END, StateGraph

from ai_engine.config.llm_config import get_llm
from ai_engine.utils.structured_outputs import generate_structured_response
from legal_grounding.citations import render_legal_context
from legal_grounding.models import LawSource, LegalContext, LegalContextAssessment
from legal_grounding.retrieval import LawRetriever, PortalLegislativSOAPRetriever


class LegalGroundingState(TypedDict, total=False):
    user_prompt: str
    case_summary: Any
    legal_search_queries: list[str]
    legal_context: LegalContext
    system_events: list[str]


def create_legal_grounding_workflow(
    *,
    retriever: LawRetriever | None = None,
    max_search_rounds: int | None = None,
    max_assessment_calls: int | None = None,
):
    resolved_retriever = retriever or PortalLegislativSOAPRetriever()
    search_limit = max_search_rounds or int(os.getenv("LEGAL_MAX_SEARCH_ROUNDS", "2"))
    assessment_limit = max_assessment_calls or int(os.getenv("LEGAL_MAX_ASSESSMENT_CALLS", "1"))
    source_limit = int(os.getenv("LEGAL_MAX_SOURCES", "8"))
    context_char_limit = int(os.getenv("LEGAL_MAX_CONTEXT_CHARS", "16000"))

    graph = StateGraph(LegalGroundingState)
    graph.add_node("prepare_legal_query", prepare_legal_query_node)
    graph.add_node(
        "retrieve_laws",
        lambda state: retrieve_laws_node(
            state,
            retriever=resolved_retriever,
            max_search_rounds=search_limit,
            max_assessment_calls=assessment_limit,
            max_sources=source_limit,
            max_context_chars=context_char_limit,
        ),
    )
    graph.add_node(
        "assess_legal_context",
        lambda state: assess_legal_context_node(
            state,
            max_assessment_calls=assessment_limit,
            max_search_rounds=search_limit,
        ),
    )
    graph.set_entry_point("prepare_legal_query")
    graph.add_edge("prepare_legal_query", "retrieve_laws")
    graph.add_conditional_edges(
        "retrieve_laws",
        lambda state: route_after_retrieval(state, max_assessment_calls=assessment_limit),
        {"assess": "assess_legal_context", "done": END},
    )
    graph.add_conditional_edges(
        "assess_legal_context",
        lambda state: route_after_assessment(state, max_search_rounds=search_limit),
        {"retrieve": "retrieve_laws", "done": END},
    )
    return graph.compile()


def prepare_legal_query_node(state: LegalGroundingState) -> dict:
    context = state.get("legal_context", LegalContext()).model_copy(deep=True)
    if not _env_flag("LEGAL_GROUNDING_ENABLED", default=True):
        return {"legal_context": context.model_copy(update={"stop_reason": "disabled"})}

    queries = _clean_queries(state.get("legal_search_queries", []))
    if not queries:
        queries = _fallback_queries(state.get("case_summary"), state.get("user_prompt", ""))
    current_query = queries[0] if queries else None
    return {
        "legal_search_queries": queries,
        "legal_context": context.model_copy(
            update={
                "current_query": current_query,
                "stop_reason": None if current_query else "no_query",
            }
        ),
    }


def retrieve_laws_node(
    state: LegalGroundingState,
    *,
    retriever: LawRetriever,
    max_search_rounds: int,
    max_assessment_calls: int,
    max_sources: int,
    max_context_chars: int,
) -> dict:
    context = state.get("legal_context", LegalContext()).model_copy(deep=True)
    events = list(state.get("system_events", []))
    if context.stop_reason in {"disabled", "no_query", "provider_error"} or not context.current_query:
        return {"legal_context": context, "system_events": events}

    query = context.current_query
    if _normalized_query(query) in {_normalized_query(item) for item in context.attempted_queries}:
        return {
            "legal_context": context.model_copy(update={"stop_reason": "no_new_results"}),
            "system_events": events,
        }

    try:
        candidates = retriever.retrieve_laws(query)
    except Exception as exc:
        warning = f"Official Romanian legislation retrieval failed: {exc}"
        print(f"[LEGAL WARNING] {warning}")
        events.append(warning)
        return {
            "legal_context": context.model_copy(
                update={
                    "attempted_queries": context.attempted_queries + [query],
                    "search_rounds": context.search_rounds + 1,
                    "new_sources_in_last_round": 0,
                    "stop_reason": "provider_error",
                    "errors": context.errors + [str(exc)],
                }
            ),
            "system_events": events,
        }

    merged_sources, new_count = _merge_sources(
        context.sources,
        candidates,
        max_sources=max_sources,
        max_context_chars=max_context_chars,
    )
    completed_rounds = context.search_rounds + 1
    stop_reason = context.stop_reason
    if completed_rounds > 1 and new_count == 0:
        stop_reason = "no_new_results"
    elif completed_rounds >= max_search_rounds:
        stop_reason = "max_search_rounds"
    elif context.assessment_calls >= max_assessment_calls:
        stop_reason = "max_assessment_calls"
    else:
        stop_reason = None

    return {
        "legal_context": context.model_copy(
            update={
                "attempted_queries": context.attempted_queries + [query],
                "sources": merged_sources,
                "search_rounds": completed_rounds,
                "new_sources_in_last_round": new_count,
                "stop_reason": stop_reason,
            }
        ),
        "system_events": events,
    }


def assess_legal_context_node(
    state: LegalGroundingState,
    *,
    max_assessment_calls: int,
    max_search_rounds: int,
) -> dict:
    context = state.get("legal_context", LegalContext()).model_copy(deep=True)
    events = list(state.get("system_events", []))
    if context.assessment_calls >= max_assessment_calls:
        return {
            "legal_context": context.model_copy(update={"stop_reason": "max_assessment_calls"}),
            "system_events": events,
        }

    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "You assess whether excerpts from official Romanian legislation are sufficient for a courtroom "
            "simulation. Do NOT answer the legal issue, argue a side, or produce a verdict. Return only the "
            "structured assessment. A refined query must be short and written in Romanian. It must search for "
            "the missing legal rule, exception, deadline, or definition.\n\n{response_contract}",
        ),
        (
            "human",
            "User prompt:\n{user_prompt}\n\nCase summary:\n{case_summary}\n\n"
            "Attempted query:\n{query}\n\nOfficial legislative excerpts:\n{legal_context}",
        ),
    ])

    try:
        result = generate_structured_response(
            llm=get_llm(temperature=0.0),
            prompt=prompt,
            variables={
                "user_prompt": state.get("user_prompt", ""),
                "case_summary": _serialize_case_summary(state.get("case_summary")),
                "query": context.current_query or "",
                "legal_context": render_legal_context(context),
            },
            schema=LegalContextAssessment,
            role_name="Legal Context Assessor",
            transport_retries=1,
            max_total_attempts=1,
            strategy_order=("function_calling",),
        )
        assessment = result.value
    except Exception as exc:
        warning = f"Legal context assessment failed: {exc}"
        print(f"[LEGAL WARNING] {warning}")
        events.append(warning)
        return {
            "legal_context": context.model_copy(
                update={
                    "assessment_calls": context.assessment_calls + 1,
                    "stop_reason": "assessment_error",
                    "errors": context.errors + [str(exc)],
                }
            ),
            "system_events": events,
        }

    next_query = assessment.next_search_query
    attempted = {_normalized_query(item) for item in context.attempted_queries}
    if next_query and _normalized_query(next_query) in attempted:
        next_query = None
    stop_reason = "sufficient" if assessment.sufficient else None
    if not assessment.sufficient and context.search_rounds >= max_search_rounds:
        stop_reason = "max_search_rounds"
    elif not assessment.sufficient and not next_query:
        stop_reason = "no_new_results"
    print(
        f"[LEGAL INFO] context_assessment sufficient={assessment.sufficient} "
        f"missing={len(assessment.missing_information)} next_query={next_query!r}"
    )

    return {
        "legal_context": context.model_copy(
            update={
                "current_query": next_query or context.current_query,
                "assessment_calls": context.assessment_calls + 1,
                "sufficient": assessment.sufficient,
                "missing_information": assessment.missing_information,
                "stop_reason": stop_reason,
            }
        ),
        "system_events": events,
    }


def route_after_retrieval(state: LegalGroundingState, *, max_assessment_calls: int) -> str:
    context = state.get("legal_context", LegalContext())
    if context.stop_reason in {
        "disabled", "no_query", "provider_error", "no_new_results", "max_assessment_calls"
    }:
        return "done"
    if context.assessment_calls >= max_assessment_calls:
        return "done"
    return "assess"


def route_after_assessment(state: LegalGroundingState, *, max_search_rounds: int) -> str:
    context = state.get("legal_context", LegalContext())
    if context.sufficient is True or context.stop_reason in {"assessment_error", "no_new_results"}:
        return "done"
    if context.search_rounds >= max_search_rounds:
        return "done"
    if not context.current_query:
        return "done"
    return "retrieve"


def _merge_sources(
    existing: list[LawSource],
    candidates: list[LawSource],
    *,
    max_sources: int,
    max_context_chars: int,
) -> tuple[list[LawSource], int]:
    merged = [source.model_copy(deep=True) for source in existing]
    seen = {_source_key(source) for source in merged}
    used_chars = sum(len(source.text) for source in merged)
    new_count = 0
    for candidate in candidates:
        key = _source_key(candidate)
        if key in seen:
            continue
        if len(merged) >= max_sources:
            break
        if used_chars + len(candidate.text) > max_context_chars:
            continue
        merged.append(candidate.model_copy(update={"id": f"LAW_{len(merged) + 1}"}))
        seen.add(key)
        used_chars += len(candidate.text)
        new_count += 1
    return merged, new_count


def _source_key(source: LawSource) -> tuple[str, str | None, str | None, str]:
    return (source.source_url, source.article, source.paragraph, " ".join(source.text.lower().split()))


def _clean_queries(queries: list[str]) -> list[str]:
    result = []
    seen = set()
    for query in queries[:3]:
        cleaned = " ".join(query.split()).strip()[:300]
        normalized = _normalized_query(cleaned)
        if cleaned and normalized not in seen:
            result.append(cleaned)
            seen.add(normalized)
    return result


def _fallback_queries(case_summary: Any, user_prompt: str) -> list[str]:
    values: list[str] = []
    if case_summary is not None:
        crime = getattr(case_summary, "crime", None)
        charges = getattr(case_summary, "charges", None)
        if isinstance(case_summary, dict):
            crime = case_summary.get("crime")
            charges = case_summary.get("charges")
        if crime:
            values.append(str(crime))
        if charges:
            values.extend(str(charge) for charge in charges)
    if not values and user_prompt:
        values.append(user_prompt)
    fallback = " ".join(values)
    return _clean_queries([fallback])


def _serialize_case_summary(case_summary: Any) -> str:
    if case_summary is None:
        return "{}"
    if hasattr(case_summary, "model_dump_json"):
        return case_summary.model_dump_json(indent=2)
    if isinstance(case_summary, dict):
        return json.dumps(case_summary, ensure_ascii=False, indent=2)
    return str(case_summary)


def _normalized_query(query: str) -> str:
    return " ".join(query.lower().split())


def _env_flag(name: str, *, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}
