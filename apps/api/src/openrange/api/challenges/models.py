"""Jeopardy challenge models: containerless CTF challenges, attachments,
solves, and the submission audit trail.

Design notes:
- Flags are stored only as sha256 hex; plaintext never touches the DB.
- ``challenge_solves`` is idempotent per (challenge, user): the UNIQUE
  constraint makes double-award races impossible at the storage layer.
- ``challenge_submissions`` keeps every normalized guess for anti-spray
  analytics; wrong-submission velocity feeds anti-cheat signals.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from openrange.api.db.base import Base, Timestamped, UUIDPrimaryKey, new_uuid
from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column


class Challenge(Base, UUIDPrimaryKey, Timestamped):
    __tablename__ = "challenges"
    __table_args__ = (
        CheckConstraint(
            "category IN ('web', 'crypto', 'pwn', 'rev', 'forensics', 'misc', 'osint')",
            name="category_valid",
        ),
        CheckConstraint("scoring IN ('static', 'dynamic')", name="scoring_valid"),
        CheckConstraint("state IN ('hidden', 'visible')", name="state_valid"),
        CheckConstraint("difficulty BETWEEN 1 AND 10", name="difficulty_range"),
    )

    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128))
    category: Mapped[str] = mapped_column(String(16))
    description: Mapped[str] = mapped_column(Text, default="")
    difficulty: Mapped[int] = mapped_column(default=5)
    points_base: Mapped[int] = mapped_column(default=100)
    scoring: Mapped[str] = mapped_column(String(8), default="static")
    # {"initial": int, "minimum": int, "solves_to_floor": int}; null when static.
    dynamic_decay: Mapped[dict[str, int] | None] = mapped_column(JSONB, nullable=True)
    flag_hash: Mapped[str] = mapped_column(String(64))
    flag_case_sensitive: Mapped[bool] = mapped_column(Boolean, default=False)
    state: Mapped[str] = mapped_column(String(8), default="hidden", index=True)
    author_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )


class ChallengeFile(Base):
    __tablename__ = "challenge_files"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    challenge_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("challenges.id", ondelete="CASCADE"), index=True
    )
    filename: Mapped[str] = mapped_column(String(255))
    size: Mapped[int] = mapped_column(BigInteger)
    sha256: Mapped[str] = mapped_column(String(64))
    storage_path: Mapped[str] = mapped_column(Text, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ChallengeSolve(Base):
    __tablename__ = "challenge_solves"
    __table_args__ = (
        UniqueConstraint("challenge_id", "user_id", name="uq_challenge_solves_challenge_user"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    challenge_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("challenges.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class ChallengeSubmission(Base):
    """Every normalized flag guess; never deleted (anti-spray evidence)."""

    __tablename__ = "challenge_submissions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    challenge_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("challenges.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    submission_norm: Mapped[str] = mapped_column(Text)
    correct: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
