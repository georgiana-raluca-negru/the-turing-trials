# backend/app/api/matches.py
"""
Match router — US4, US5, US7.

Endpoints:
  POST   /api/matches              create a new match (prompt + role) — US4, US5
  GET    /api/matches              list the current user's matches — US3
  GET    /api/matches/{match_id}   get full match detail (case file) — US7
  DELETE /api/matches/{match_id}   abandon / cancel a match
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.match import Match, MatchStatus, Verdict
from app.models.user import User
from app.schemas.match import MatchCreate, MatchListOut, MatchOut

router = APIRouter(prefix="/api/matches", tags=["Matches"])


@router.post(
    "/",
    response_model=MatchOut,
    status_code=status.HTTP_201_CREATED,
    summary="US4 + US5 — Create a new match with prompt and role selection",
)
async def create_match(
    body: MatchCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MatchOut:
    """
    US4: Player inputs a prompt to seed the AI Clerk.
    US5: Player selects their role (Defense Attorney, Prosecutor, Judge, Spectator).

    The AI Clerk integration (case_file_json generation) will be wired here
    once the LangGraph agent is implemented. For now the match is created in
    LOBBY status with an empty case_file_json.
    """
    match = Match(
        player_id=current_user.id,
        player_prompt=body.player_prompt,
        player_role=body.player_role,
        total_rounds=body.max_rounds,
        status=MatchStatus.LOBBY,
        verdict=Verdict.PENDING,
    )
    db.add(match)

    # Note: total_matches is incremented when the game session actually starts,
    # not at match creation time (a LOBBY match hasn't been played yet).

    await db.commit()
    await db.refresh(match)
    return MatchOut.model_validate(match)


@router.get(
    "/",
    response_model=list[MatchListOut],
    summary="List the current user's matches (US3)",
)
async def list_matches(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[MatchListOut]:
    result = await db.execute(
        select(Match)
        .where(Match.player_id == current_user.id)
        .order_by(Match.created_at.desc())
    )
    matches = result.scalars().all()
    return [MatchListOut.model_validate(m) for m in matches]


@router.get(
    "/{match_id}",
    response_model=MatchOut,
    summary="US7 — Get full match detail including case file",
)
async def get_match(
    match_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MatchOut:
    """
    US7: As a player, I want a fixed summary of the case (Crime and Charges)
    always visible so that I don't lose track of essential details during debates.
    """
    match = await _get_match_or_404(match_id, current_user.id, db)
    return MatchOut.model_validate(match)


@router.delete(
    "/{match_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Abandon / cancel a match",
)
async def abandon_match(
    match_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    match = await _get_match_or_404(match_id, current_user.id, db)

    if match.status == MatchStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot abandon a completed match",
        )

    match.status = MatchStatus.ABANDONED
    match.completed_at = datetime.now(timezone.utc)
    await db.commit()


# ── Internal helper ───────────────────────────────────────────────────────────

async def _get_match_or_404(
    match_id: uuid.UUID, player_id: uuid.UUID, db: AsyncSession
) -> Match:
    result = await db.execute(
        select(Match).where(Match.id == match_id, Match.player_id == player_id)
    )
    match = result.scalar_one_or_none()
    if match is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found")
    return match
