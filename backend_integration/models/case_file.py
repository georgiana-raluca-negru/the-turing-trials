from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class EvidenceRole(str, Enum):
    PROSECUTION = "prosecution"
    DEFENSE = "defense"
    SHARED = "shared"


class CaseSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    crime: str = Field(..., min_length=1)
    charges: list[str] = Field(..., min_length=1)
    background_story: str = Field(..., min_length=1)


class EvidenceCard(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    code: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    evidence_type: str = Field(..., min_length=1)
    assigned_role: EvidenceRole
    backend_id: str | None = None
    is_used: bool = False
    used_in_turn_index: int | None = None


class CaseFileBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: CaseSummary
    prosecution_evidence: list[EvidenceCard] = Field(default_factory=list)
    defense_evidence: list[EvidenceCard] = Field(default_factory=list)
    shared_evidence: list[EvidenceCard] = Field(default_factory=list)
