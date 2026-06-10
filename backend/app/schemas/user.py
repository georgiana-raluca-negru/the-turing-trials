# backend/app/schemas/user.py
"""
Schemas for user profile and dashboard (US3).
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, model_validator

_RANK_K = 5  # Bayesian prior constant — penalises low sample sizes


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
    match_result: str = "n/a"   # "win" | "loss" | "n/a"

    model_config = {"from_attributes": True}

    @model_validator(mode="after")
    def compute_result(self) -> "MatchSummary":
        if self.player_role == "defense_attorney":
            if self.verdict == "not_guilty":
                self.match_result = "win"
            elif self.verdict == "guilty":
                self.match_result = "loss"
        elif self.player_role == "prosecutor":
            if self.verdict == "guilty":
                self.match_result = "win"
            elif self.verdict == "not_guilty":
                self.match_result = "loss"
        return self


class DashboardOut(BaseModel):
    """US3 — full dashboard payload."""
    user: UserOut
    total_matches: int
    total_wins: int
    win_rate: float                   # 0.0 – 1.0
    recent_matches: list[MatchSummary]


class LeaderboardEntry(BaseModel):
    rank: int
    username: str
    total_matches: int
    total_wins: int
    win_rate: float       # raw 0.0–1.0
    score: float          # Bayesian score used for ranking


class LeaderboardOut(BaseModel):
    entries: list[LeaderboardEntry]
    total_players: int
