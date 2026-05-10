# backend/app/api/evidence.py
"""
Evidence inventory router — US6, US8, US9, US10.

Endpoints:
  GET  /api/matches/{match_id}/evidence        role-filtered card list — US6, US8
  POST /api/matches/{match_id}/evidence        bulk-create cards (AI Clerk) — US6
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
from app.schemas.evidence import EvidenceBulkCreate, EvidenceCardOut

router = APIRouter(
    prefix="/api/matches/{match_id}/evidence",
    tags=["Evidence"],
)


# ── Role → visible evidence mapping (US6) ─────────────────────────────────────
_ROLE_VISIBILITY: dict[PlayerRole, set[EvidenceRole]] = {
    PlayerRole.DEFENSE_ATTORNEY: {EvidenceRole.DEFENSE, EvidenceRole.SHARED},
    PlayerRole.PROSECUTOR:       {EvidenceRole.PROSECUTION, EvidenceRole.SHARED},
    PlayerRole.JUDGE:            {EvidenceRole.DEFENSE, EvidenceRole.PROSECUTION, EvidenceRole.SHARED},
    PlayerRole.SPECTATOR:        {EvidenceRole.SHARED},
}


@router.get(
    "/",
    response_model=list[EvidenceCardOut],
    summary="US6 + US8 — Get role-filtered evidence cards for this match",
)
async def get_evidence(
    match_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[EvidenceCardOut]:
    """
    US6: Evidence is distributed only to the appropriate role.
    US8: Returns the player's visual Evidence Folder cards.

    Defense Attorney → sees only DEFENSE + SHARED cards.
    Prosecutor       → sees only PROSECUTION + SHARED cards.
    Judge            → sees all cards (to score arguments).
    Spectator        → sees only SHARED cards.
    """
    match = await _get_match_or_404(match_id, current_user.id, db)

    visible_roles = _ROLE_VISIBILITY.get(match.player_role, {EvidenceRole.SHARED})

    result = await db.execute(
        select(Evidence)
        .where(
            Evidence.match_id == match_id,
            Evidence.assigned_role.in_(visible_roles),
        )
        .order_by(Evidence.card_order)
    )
    cards = result.scalars().all()
    return [EvidenceCardOut.model_validate(c) for c in cards]


@router.post(
    "/",
    response_model=list[EvidenceCardOut],
    status_code=status.HTTP_201_CREATED,
    summary="US6 — Bulk-create evidence cards (called by AI Clerk)",
)
async def create_evidence(
    match_id: uuid.UUID,
    body: EvidenceBulkCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[EvidenceCardOut]:
    """
    The AI Clerk calls this endpoint after generating the case file to
    populate the Evidence Inventory for a match (US6).
    """
    match = await _get_match_or_404(match_id, current_user.id, db)

    cards: list[Evidence] = []
    for item in body.cards:
        card = Evidence(
            match_id=match.id,
            title=item.title,
            description=item.description,
            assigned_role=item.assigned_role,
            card_order=item.card_order,
        )
        db.add(card)
        cards.append(card)

    await db.commit()
    for card in cards:
        await db.refresh(card)

    return [EvidenceCardOut.model_validate(c) for c in cards]


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
