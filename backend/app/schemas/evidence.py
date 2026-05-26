# backend/app/schemas/evidence.py
"""
Schemas for the Evidence Inventory (US6, US8, US9, US10).
"""

import uuid

from pydantic import BaseModel, Field

from app.models.evidence import EvidenceRole


class EvidenceCardOut(BaseModel):
    """A single evidence card shown in the Evidence Folder (US8)."""
    id: uuid.UUID
    title: str
    description: str
    assigned_role: EvidenceRole
    card_order: int
    is_used: bool
    used_in_round: int | None

    model_config = {"from_attributes": True}


class EvidenceCreateItem(BaseModel):
    """One card inside a bulk-create request."""
    title: str = Field(..., min_length=2, max_length=200)
    description: str = Field(..., min_length=5)
    assigned_role: EvidenceRole
    card_order: int = 0


class EvidenceBulkCreate(BaseModel):
    """
    US6 — AI Clerk posts all generated evidence cards for a match at once.
    """
    cards: list[EvidenceCreateItem] = Field(..., min_length=1)
