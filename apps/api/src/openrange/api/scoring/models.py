"""Scoring models: immutable score events, adjustments, achievements,
leaderboard snapshots, and anti-cheat signals (plan Phase 9).

Invariants baked into the schema:
- ``score_events`` is INSERT-ONLY. Reversals never UPDATE or DELETE rows;
  they append an ``adjustment`` event linked through ``score_adjustments``.
- ``idempotency_key`` makes event ingestion exactly-once per key.
- Achievements are data-driven: rules live in ``achievements_catalog``
  and awards are unique per (user, slug).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from openrange.api.db.base import Base
from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column


class ScoreEvent(Base):
    """Append-only scoring ledger row."""

    __tablename__ = "score_events"
    __table_args__ = (Index("ix_score_events_user_kind_created", "user_id", "kind", "created_at"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String(32))
    ref_slug: Mapped[str | None] = mapped_column(String(64), index=True)
    points: Mapped[int] = mapped_column(default=0)
    xp: Mapped[int] = mapped_column(default=0)
    meta: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    idempotency_key: Mapped[str | None] = mapped_column(Text, unique=True)


class ScoreAdjustment(Base):
    """Audit trail linking a reversal/adjustment to its original event."""

    __tablename__ = "score_adjustments"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    adjustment_event_id: Mapped[int] = mapped_column(
        ForeignKey("score_events.id", ondelete="CASCADE"), index=True
    )
    original_event_id: Mapped[int | None] = mapped_column(
        ForeignKey("score_events.id", ondelete="CASCADE"), index=True
    )
    target_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    reason: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AchievementCatalog(Base):
    """Data-driven achievement rule, e.g.

    {"type": "count", "event": "room_solve", "track": "web", "threshold": 5}
    """

    __tablename__ = "achievements_catalog"

    slug: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    description: Mapped[str] = mapped_column(Text, default="")
    rule: Mapped[dict[str, Any]] = mapped_column(JSONB)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class UserAchievement(Base):
    __tablename__ = "user_achievements"
    __table_args__ = (UniqueConstraint("user_id", "slug", name="uq_user_achievements_user_slug"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    slug: Mapped[str] = mapped_column(
        String(64), ForeignKey("achievements_catalog.slug", ondelete="CASCADE")
    )
    awarded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LeaderboardSnapshot(Base):
    """Frozen projection output for a (scope, period_key) pair."""

    __tablename__ = "leaderboard_snapshots"

    scope: Mapped[str] = mapped_column(String(16), primary_key=True)
    period_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    payload: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class AntiCheatSignal(Base):
    """Reviewable cheating signal; never auto-bans (plan Phase 9.9)."""

    __tablename__ = "anti_cheat_signals"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String(32))
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    status: Mapped[str] = mapped_column(String(16), default="open", index=True)
    review_note: Mapped[str] = mapped_column(Text, default="")
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    reviewed_at: Mapped[datetime | None]
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
