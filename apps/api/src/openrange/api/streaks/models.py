"""Streaks models: per-user timezone profile, cached streak state, and
global freeze days (plan Phase 9 item 5).

- ``streak_profiles`` carries everything personal: timezone, anchored
  week start, one self-service freeze day, reminder opt-in.
- ``streak_states`` is a cache derived from ``score_events`` history;
  it can always be rebuilt and never drives money or access.
- ``streak_freezes`` are platform-wide grace days set by admins.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from openrange.api.db.base import Base, Timestamped
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column


class StreakProfile(Base, Timestamped):
    """Per-user streak preferences."""

    __tablename__ = "streak_profiles"
    __table_args__ = (
        CheckConstraint("weekly_anchor BETWEEN 0 AND 6", name="ck_streak_profiles_anchor_range"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    tz: Mapped[str] = mapped_column(String(64), default="UTC")
    weekly_anchor: Mapped[int] = mapped_column(SmallInteger, default=0)  # 0=Monday .. 6=Sunday
    freeze_date: Mapped[date | None]  # one self-service freeze day
    reminders_enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class StreakState(Base):
    """Derived streak counters for one user (rebuildable cache)."""

    __tablename__ = "streak_states"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    current_daily: Mapped[int] = mapped_column(Integer, default=0)
    longest_daily: Mapped[int] = mapped_column(Integer, default=0)
    last_completion_date: Mapped[date | None]
    current_weekly: Mapped[int] = mapped_column(Integer, default=0)
    longest_weekly: Mapped[int] = mapped_column(Integer, default=0)
    week_key: Mapped[str | None] = mapped_column(String(16))


class StreakFreeze(Base):
    """Platform-wide freeze day; chain continuity is granted once per date."""

    __tablename__ = "streak_freezes"

    freeze_date: Mapped[date] = mapped_column(Date, primary_key=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
