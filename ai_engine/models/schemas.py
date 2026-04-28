from pydantic import BaseModel, Field
from typing import List, Optional

class Evidence(BaseModel):
    id: str = Field(default="EVD-UNKNOWN", description="Unique identifier for the evidence (e.g., EVD-001)")
    title: str = Field(default="Untitled Evidence", description="Short title of the evidence")
    description: str = Field(default="No description provided.", description="Detailed description of what the evidence is")
    type: str = Field(default="Document", description="Type of evidence (e.g., Document, Testimony, Physical)")
    is_used: bool = Field(default=False, description="Whether the evidence has been used in the trial")

class CaseContext(BaseModel):
    crime: str = Field(default="Unknown Crime", description="The crime that was committed")
    charges: List[str] = Field(default_factory=list, description="List of specific charges against the defendant")
    background_story: str = Field(default="No background story provided.", description="Background story and details of the case")

class Argument(BaseModel):
    speaker: str = Field(default="Unknown", description="The speaker of the argument (Prosecutor, Defense, Judge)")
    text: str = Field(default="No argument text provided.", description="The actual text spoken by the agent")
    attached_evidence_ids: List[str] = Field(default_factory=list, description="List of evidence IDs used in this argument")

class CaseFile(BaseModel):
    case_summary: CaseContext = Field(default_factory=lambda: CaseContext())
    defense_evidence: List[Evidence] = Field(default_factory=list)
    prosecution_evidence: List[Evidence] = Field(default_factory=list)

class Verdict(BaseModel):
    guilty: bool = Field(default=False, description="True if the defendant is found guilty, False otherwise.")
    reasoning: str = Field(default="No reasoning provided.", description="The judge's detailed reasoning for the verdict based on the arguments and evidence presented.")
    defense_score: int = Field(default=5, description="Score for the defense's performance (1-10).")
    prosecution_score: int = Field(default=5, description="Score for the prosecution's performance (1-10).")