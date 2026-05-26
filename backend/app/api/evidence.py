# backend/app/api/evidence.py
"""
Evidence router — US6, US8, US9, US10.

Endpoints:
  GET /api/evidence/{match_id}              list evidence for the player's role (US6, US8)
  GET /api/evidence/{match_id}/{evidence_id}  get single evidence card detail
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.evidence import Evidence, EvidenceRole
from app.models.match import Match, PlayerRole
from app.models.user import User
from app.schemas.evidence import EvidenceCardOut

router = APIRouter(prefix="/api/evidence", tags=["Evidence"])


# ── Role → visible evidence roles ────────────────────────────────────────────
_ROLE_EVIDENCE_MAP: dict[PlayerRole, list[EvidenceRole]] = {
    PlayerRole.DEFENSE_ATTORNEY: [EvidenceRole.DEFENSE, EvidenceRole.SHARED],
    PlayerRole.PROSECUTOR: [EvidenceRole.PROSECUTION, EvidenceRole.SHARED],
    PlayerRole.JUDGE: [EvidenceRole.DEFENSE, EvidenceRole.PROSECUTION, EvidenceRole.SHARED],
    PlayerRole.SPECTATOR: [],  # no evidence for spectators
}


@router.get(
    "/{match_id}",
    response_model=list[EvidenceCardOut],
    summary="US6 + US8 — List evidence cards visible to the player's role",
)
async def list_evidence(
    match_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[EvidenceCardOut]:
    """
    US6: Evidence is distributed only to the appropriate role.
    US8: Visual Evidence Folder displaying cards the player can consult.

    Defense players see defense + shared evidence.
    Prosecutors see prosecution + shared evidence.
    Judges see all evidence.
    Spectators see no evidence.
    """
    # Verify ownership
    match = await _get_user_match(match_id, current_user.id, db)

    allowed_roles = _ROLE_EVIDENCE_MAP.get(match.player_role, [])
    if not allowed_roles:
        return []

    result = await db.execute(
        select(Evidence)
        .where(
            Evidence.match_id == match_id,
            Evidence.assigned_role.in_(allowed_roles),
        )
        .order_by(Evidence.card_order)
    )
    evidence_items = result.scalars().all()
    return [EvidenceCardOut.model_validate(e) for e in evidence_items]


@router.get(
    "/{match_id}/{evidence_id}",
    response_model=EvidenceCardOut,
    summary="Get a single evidence card",
)
async def get_evidence(
    match_id: uuid.UUID,
    evidence_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EvidenceCardOut:
    """Retrieve a specific evidence card, checking role-based visibility."""
    match = await _get_user_match(match_id, current_user.id, db)

    allowed_roles = _ROLE_EVIDENCE_MAP.get(match.player_role, [])
    if not allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Spectators cannot view evidence",
        )

    result = await db.execute(
        select(Evidence).where(
            Evidence.id == evidence_id,
            Evidence.match_id == match_id,
            Evidence.assigned_role.in_(allowed_roles),
        )
    )
    evidence = result.scalar_one_or_none()
    if evidence is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence not found or not visible to your role",
        )
    return EvidenceCardOut.model_validate(evidence)


# ── Internal helper ───────────────────────────────────────────────────────────

async def _get_user_match(
    match_id: uuid.UUID, player_id: uuid.UUID, db: AsyncSession
) -> Match:
    result = await db.execute(
        select(Match).where(Match.id == match_id, Match.player_id == player_id)
    )
    match = result.scalar_one_or_none()
    if match is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match not found",
        )
    return match
