# backend/app/models/round.py
"""
Round model — one row per argument turn inside a GameSession.

Covers:
  US9:  A player selects an evidence card and attaches it to their argument.
  US10: Evidence cards that have been used are tracked (via evidence.is_used).
  US11: Objection mechanic — the opponent can interrupt; the objection text
        and the AI's response are stored on the round that was interrupted.
  US12: The AI Judge's per-round score delta updates scales_value on GameSession.
"""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class RoundSpeaker(str, enum.Enum):
    """Who submitted this round's argument."""
    PLAYER = "player"
    AI_DEFENSE = "ai_defense"
    AI_PROSECUTION = "ai_prosecution"
    AI_JUDGE = "ai_judge"


class Round(Base):
    __tablename__ = "rounds"

    # ── Primary key ──────────────────────────────────────────────────────────
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # ── Parent session ────────────────────────────────────────────────────────
    game_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("game_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Round position ────────────────────────────────────────────────────────
    round_number: Mapped[int] = mapped_column(Integer, nullable=False)
    speaker: Mapped[RoundSpeaker] = mapped_column(
        Enum(RoundSpeaker, name="round_speaker_enum"),
        nullable=False,
    )

    # ── Argument text ─────────────────────────────────────────────────────────
    argument_text: Mapped[str] = mapped_column(Text, nullable=False)

    # ── Attached evidence (US9) — stores the evidence UUID as text ───────────
    # The Evidence row itself is marked is_used=True after this round.
    attached_evidence_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evidence.id", ondelete="SET NULL"),
        nullable=True,
    )

    # ── Objection mechanic (US11) ─────────────────────────────────────────────
    was_objected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    objection_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    objection_response: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Per-round Judge scoring (US12) ────────────────────────────────────────
    # Delta applied to GameSession.scales_value after this round
    # Positive → defense advantage; Negative → prosecution advantage
    scales_delta: Mapped[float | None] = mapped_column(Float, nullable=True)
    judge_feedback: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Timestamp ─────────────────────────────────────────────────────────────
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    game_session: Mapped["GameSession"] = relationship(
        "GameSession", back_populates="rounds"
    )
    attached_evidence: Mapped["Evidence | None"] = relationship(
        "Evidence", foreign_keys=[attached_evidence_id]
    )

    def __repr__(self) -> str:
        return (
            f"<Round #{self.round_number} speaker={self.speaker} "
            f"objected={self.was_objected}>"
        )
