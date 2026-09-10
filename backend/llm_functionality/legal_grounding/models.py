from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class LawSource(BaseModel):
    """A citable excerpt retrieved from an official Romanian legislative act."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    id: str = ""
    document_id: str | None = None
    law: str = Field(..., min_length=1)
    act_type: str | None = None
    act_number: str | None = None
    article: str | None = None
    paragraph: str | None = None
    text: str = Field(..., min_length=1)
    issuer: str | None = None
    publication: str | None = None
    effective_date: str | None = None
    version_date: str | None = None
    status: str | None = None
    source_url: str = Field(..., min_length=1)
    relevance_score: float = 0.0


class LegalContext(BaseModel):
    """Bounded, per-match state for live legal retrieval."""

    model_config = ConfigDict(extra="forbid")

    current_query: str | None = None
    attempted_queries: list[str] = Field(default_factory=list)
    sources: list[LawSource] = Field(default_factory=list)
    search_rounds: int = Field(default=0, ge=0)
    assessment_calls: int = Field(default=0, ge=0)
    sufficient: bool | None = None
    missing_information: list[str] = Field(default_factory=list)
    new_sources_in_last_round: int = Field(default=0, ge=0)
    stop_reason: Literal[
        "disabled",
        "sufficient",
        "max_search_rounds",
        "max_assessment_calls",
        "no_new_results",
        "no_query",
        "provider_error",
        "assessment_error",
    ] | None = None
    errors: list[str] = Field(default_factory=list)


class LegalContextAssessment(BaseModel):
    """Structured output of the only additional LLM responsibility."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    sufficient: bool
    missing_information: list[str] = Field(default_factory=list)
    next_search_query: str | None = None

    @field_validator("missing_information")
    @classmethod
    def clean_missing_information(cls, values: list[str]) -> list[str]:
        return [value.strip() for value in values if value and value.strip()]

    @field_validator("next_search_query")
    @classmethod
    def clean_next_query(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = " ".join(value.split()).strip()
        return cleaned or None
