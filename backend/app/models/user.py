# backend/app/models/user.py
"""
User model — covers US1, US2, US3.

US1: A visitor can register with email/password or via Google/GitHub OAuth.
US2: An authenticated user can securely log out (handled by auth logic;
     the model stores the data needed for session invalidation).
US3: A user Dashboard shows match history — the relationship to Match
     provides this data.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    # ── Primary key ──────────────────────────────────────────────────────────
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )

    # ── Identity ─────────────────────────────────────────────────────────────
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)

    # ── Password auth (nullable → OAuth-only users have no password) ─────────
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # ── OAuth (US1 — Google / GitHub) ────────────────────────────────────────
    oauth_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)   # "google" | "github" | None
    oauth_sub: Mapped[str | None] = mapped_column(String(255), nullable=True)        # Provider's user ID

    # ── Account state ────────────────────────────────────────────────────────
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # ── Aggregate stats (denormalised for US3 Dashboard speed) ───────────────
    total_matches: Mapped[int] = mapped_column(default=0, nullable=False)
    total_wins: Mapped[int] = mapped_column(default=0, nullable=False)

    # ── Timestamps ───────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
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
    matches: Mapped[list["Match"]] = relationship(
        "Match",
        back_populates="player",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} username={self.username!r}>"
