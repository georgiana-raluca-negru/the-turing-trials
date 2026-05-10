# backend/app/models/match.py
"""
Match model — covers US3, US4, US5, US13.

US3:  A user's Dashboard shows role played, case summary, verdict, date.
US4:  A player inputs a prompt to seed the AI Clerk case generation.
US5:  A player selects a role (Defense Attorney, Prosecutor, Judge, Spectator).
US13: The Judge ends the trial; a motivated Guilty/Not Guilty verdict is saved.
"""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PlayerRole(str, enum.Enum):
    """US5 — the four playable roles."""
    DEFENSE_ATTORNEY = "defense_attorney"
    PROSECUTOR = "prosecutor"
    JUDGE = "judge"
    SPECTATOR = "spectator"


class Verdict(str, enum.Enum):
    """US13 — possible final verdicts."""
    GUILTY = "guilty"
    NOT_GUILTY = "not_guilty"
    PENDING = "pending"   # while the match is still in progress


class MatchStatus(str, enum.Enum):
    LOBBY = "lobby"           # created, waiting for session to start
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class Match(Base):
    __tablename__ = "matches"

    # ── Primary key ──────────────────────────────────────────────────────────
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )

    # ── Owner (the human player — foreign key to users) ──────────────────────
    player_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Case generation (US4) ─────────────────────────────────────────────────
    player_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    # Full structured case file produced by the AI Clerk (stored as JSON text)
    case_file_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    case_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Role selection (US5) ──────────────────────────────────────────────────
    player_role: Mapped[PlayerRole] = mapped_column(
        Enum(PlayerRole, name="player_role_enum"),
        nullable=False,
    )

    # ── Match lifecycle ───────────────────────────────────────────────────────
    status: Mapped[MatchStatus] = mapped_column(
        Enum(MatchStatus, name="match_status_enum"),
        default=MatchStatus.LOBBY,
        nullable=False,
    )
    total_rounds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # ── Verdict (US13) ────────────────────────────────────────────────────────
    verdict: Mapped[Verdict] = mapped_column(
        Enum(Verdict, name="verdict_enum"),
        default=Verdict.PENDING,
        nullable=False,
    )
    verdict_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Timestamps ───────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    player: Mapped["User"] = relationship("User", back_populates="matches")

    game_session: Mapped["GameSession | None"] = relationship(
        "GameSession",
        back_populates="match",
        cascade="all, delete-orphan",
        uselist=False,   # one-to-one
    )

    evidence_items: Mapped[list["Evidence"]] = relationship(
        "Evidence",
        back_populates="match",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<Match id={self.id} role={self.player_role} "
            f"verdict={self.verdict} status={self.status}>"
        )
