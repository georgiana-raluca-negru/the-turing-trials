from typing import List, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

class Evidence(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    id: str = Field(..., min_length=1, description="Unique identifier for the evidence (e.g., EVD-001)")
    title: str = Field(..., min_length=1, description="Short title of the evidence")
    description: str = Field(..., min_length=1, description="Detailed description of what the evidence is")
    type: str = Field(..., min_length=1, description="Type of evidence (e.g., Document, Testimony, Physical)")
    is_used: bool = Field(default=False, description="Whether the evidence has been used in the trial")

class CaseContext(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    crime: str = Field(..., min_length=1, description="The crime that was committed")
    charges: List[str] = Field(..., min_length=1, description="List of specific charges against the defendant")
    background_story: str = Field(..., min_length=1, description="Background story and details of the case")

    @field_validator("charges")
    @classmethod
    def validate_charges(cls, value: List[str]) -> List[str]:
        return _strip_non_empty_strings(value)

class Argument(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    speaker: Literal["Prosecutor", "Defense", "Judge", "System"] = Field(
        ...,
        description="The speaker of the argument (Prosecutor, Defense, Judge, System)"
    )
    text: str = Field(..., min_length=1, description="The actual text spoken by the agent")
    attached_evidence_ids: List[str] = Field(default_factory=list, description="List of evidence IDs used in this argument")

    @field_validator("attached_evidence_ids")
    @classmethod
    def validate_attached_evidence_ids(cls, value: List[str]) -> List[str]:
        return [item.strip() for item in value if item and item.strip()]

class CaseFile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_summary: CaseContext
    defense_evidence: List[Evidence] = Field(..., min_length=1)
    prosecution_evidence: List[Evidence] = Field(..., min_length=1)

class Verdict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    guilty: bool = Field(..., description="True if the defendant is found guilty, False otherwise.")
    reasoning: str = Field(..., min_length=1, description="The judge's detailed reasoning for the verdict based on the arguments and evidence presented.")
    defense_score: int = Field(..., ge=1, le=10, description="Score for the defense's performance (1-10).")
    prosecution_score: int = Field(..., ge=1, le=10, description="Score for the prosecution's performance (1-10).")


class TurnOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    text: str = Field(..., min_length=1, description="The actual text spoken by the agent.")
    attached_evidence_ids: List[str] = Field(
        default_factory=list,
        description="List of evidence IDs used in this argument."
    )

    @field_validator("attached_evidence_ids")
    @classmethod
    def validate_attached_evidence_ids(cls, value: List[str]) -> List[str]:
        return [item.strip() for item in value if item and item.strip()]


def _strip_non_empty_strings(values: List[str]) -> List[str]:
    cleaned_values = [value.strip() for value in values if value and value.strip()]
    if not cleaned_values:
        raise ValueError("At least one non-empty value is required.")
    return cleaned_values
