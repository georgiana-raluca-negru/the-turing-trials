# backend/app/api/users.py
"""
User profile and dashboard router — US3.

Endpoints:
  GET /api/users/me             current user profile
  GET /api/users/me/dashboard   match history, win rate, stats
"""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.match import Match
from app.models.user import User
from app.schemas.user import DashboardOut, LeaderboardEntry, LeaderboardOut, MatchSummary, UserOut

_RANK_K = 5

router = APIRouter(prefix="/api/users", tags=["Users"])


@router.get(
    "/me",
    response_model=UserOut,
    summary="Return the authenticated user's profile",
)
async def get_me(current_user: User = Depends(get_current_user)) -> UserOut:
    return UserOut.model_validate(current_user)


@router.get(
    "/me/dashboard",
    response_model=DashboardOut,
    summary="US3 — Match history, win rate, and stats for the current user",
)
async def get_dashboard(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DashboardOut:
    """
    US3: As a user, I want a Dashboard showing my match history
    (role played, case summary, verdict, date) so that I can track my
    progress and overall win rate.
    """
    result = await db.execute(
        select(Match)
        .where(Match.player_id == current_user.id)
        .order_by(Match.created_at.desc())
        .limit(50)
    )
    matches = result.scalars().all()

    total = current_user.total_matches
    wins = current_user.total_wins
    win_rate = (wins / total) if total > 0 else 0.0

    return DashboardOut(
        user=UserOut.model_validate(current_user),
        total_matches=total,
        total_wins=wins,
        win_rate=round(win_rate, 4),
        recent_matches=[MatchSummary.model_validate(m) for m in matches],
    )


@router.get(
    "/leaderboard",
    response_model=LeaderboardOut,
    summary="Global leaderboard ranked by Bayesian win score",
)
async def get_leaderboard(db: AsyncSession = Depends(get_db)) -> LeaderboardOut:
    """
    Returns all users who have played at least one ranked match,
    sorted by Bayesian score = wins / (matches + K).
    This rewards consistent performance over a large number of games,
    preventing a player with 1 win from outranking one with 99 wins.
    """
    result = await db.execute(
        select(User).where(User.total_matches > 0)
    )
    users = result.scalars().all()

    def bayesian_score(u: User) -> float:
        return u.total_wins / (u.total_matches + _RANK_K)

    ranked = sorted(users, key=bayesian_score, reverse=True)

    entries = [
        LeaderboardEntry(
            rank=i + 1,
            username=u.username,
            total_matches=u.total_matches,
            total_wins=u.total_wins,
            win_rate=round(u.total_wins / u.total_matches, 4),
            score=round(bayesian_score(u), 4),
        )
        for i, u in enumerate(ranked)
    ]

    return LeaderboardOut(entries=entries, total_players=len(entries))
