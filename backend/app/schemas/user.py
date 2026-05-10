# backend/app/schemas/user.py
"""
Schemas for user profile and dashboard (US3).
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr


class UserOut(BaseModel):
    """Public user profile — never exposes hashed_password or oauth_sub."""
    id: uuid.UUID
    username: str
    email: EmailStr
    is_active: bool
    is_verified: bool
    total_matches: int
    total_wins: int
    created_at: datetime

    model_config = {"from_attributes": True}


class MatchSummary(BaseModel):
    """Compact match record used in the dashboard (US3)."""
    id: uuid.UUID
    player_role: str
    case_summary: str | None
    verdict: str
    status: str
    created_at: datetime
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class DashboardOut(BaseModel):
    """US3 — full dashboard payload."""
    user: UserOut
    total_matches: int
    total_wins: int
    win_rate: float                   # 0.0 – 1.0
    recent_matches: list[MatchSummary]
