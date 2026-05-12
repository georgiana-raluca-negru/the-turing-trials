# backend/app/models/game_session.py
"""
GameSession model — the live courtroom state for a single Match.

Covers:
  US12: Scales of Justice — real-time progress bar value persisted here.
  US13: Number of rounds completed tracked here so the Judge can end the trial.

One Match has exactly one GameSession (one-to-one).
The Session holds the running chat/argument transcript and the current
Scales-of-Justice score so it can be recovered after a reconnect.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class GameSession(Base):
    __tablename__ = "game_sessions"

    # ── Primary key ──────────────────────────────────────────────────────────
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )

    # ── Parent match (one-to-one) ─────────────────────────────────────────────
    match_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("matches.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    # ── Turn tracking ─────────────────────────────────────────────────────────
    current_round: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    max_rounds: Mapped[int] = mapped_column(Integer, default=5, nullable=False)

    # ── Whose turn it is right now ("defense_attorney" | "prosecutor" | "judge")
    current_turn: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )

    # ── Scales of Justice (US12) ──────────────────────────────────────────────
    # Range: -1.0 (full prosecution advantage) → +1.0 (full defense advantage)
    # 0.0 = perfectly balanced
    scales_value: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # ── Full chat/argument transcript (JSON array stored as text) ────────────
    # Kept here for AI Judge context (US13) and WebSocket reconnect replay
    transcript_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Timestamps ───────────────────────────────────────────────────────────
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    match: Mapped["Match"] = relationship("Match", back_populates="game_session")

    rounds: Mapped[list["Round"]] = relationship(
        "Round",
        back_populates="game_session",
        cascade="all, delete-orphan",
        order_by="Round.round_number",
    )

    def __repr__(self) -> str:
        return (
            f"<GameSession id={self.id} match_id={self.match_id} "
            f"round={self.current_round}/{self.max_rounds} "
            f"scales={self.scales_value:+.2f}>"
        )
