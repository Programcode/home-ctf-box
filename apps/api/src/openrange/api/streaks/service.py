"""Streaks service: reads ``score_events`` read-only, refreshes cached
state, and persists profiles and freeze days.

This module never writes to scoring tables; the ledger stays owned by
the scoring package (plan Phase 9 boundary).
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from openrange.api.config import get_settings
from openrange.api.scoring.models import ScoreEvent
from openrange.api.streaks import engine
from openrange.api.streaks.engine import ReminderPrefs, StreakStateData
from openrange.api.streaks.models import StreakFreeze, StreakProfile, StreakState
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

COMPLETION_KIND = "room_solve"


class StreakServiceError(Exception):
    def __init__(self, code: str, status: int = 400) -> None:
        super().__init__(code)
        self.code = code
        self.status = status


async def get_or_create_profile(db: AsyncSession, *, user_id: uuid.UUID) -> StreakProfile:
    profile = await db.get(StreakProfile, user_id)
    if profile is None:
        profile = StreakProfile(user_id=user_id)
        db.add(profile)
        await db.flush()
    return profile


async def get_or_create_state(db: AsyncSession, *, user_id: uuid.UUID) -> StreakState:
    state = await db.get(StreakState, user_id)
    if state is None:
        state = StreakState(user_id=user_id)
        db.add(state)
        await db.flush()
    return state


def _snapshot(state: StreakState) -> StreakStateData:
    return StreakStateData(
        current_daily=state.current_daily,
        longest_daily=state.longest_daily,
        last_completion_date=state.last_completion_date,
        current_weekly=state.current_weekly,
        longest_weekly=state.longest_weekly,
        week_key=state.week_key,
    )


def resolve_zone(tz: str) -> ZoneInfo:
    try:
        return ZoneInfo(tz)
    except Exception as exc:
        raise StreakServiceError("invalid_timezone", 422) from exc


def streak_view(
    data: StreakStateData,
    *,
    today: date,
    active_days: int,
    threshold: int,
) -> dict[str, object]:
    target, hint = engine.next_milestone_hint(
        data.current_daily,
        active_days,
        threshold,
        weekly_streak_alive=data.current_weekly > 0,
    )
    return {
        "daily": {
            "current": data.current_daily,
            "longest": data.longest_daily,
            "last_completion_date": (
                data.last_completion_date.isoformat() if data.last_completion_date else None
            ),
        },
        "weekly": {
            "current": data.current_weekly,
            "longest": data.longest_weekly,
            "week_key": data.week_key,
            "week_progress": {
                "active_days": active_days,
                "threshold": threshold,
                "remaining": max(threshold - active_days, 0),
            },
        },
        "next_milestone": {"target": target, "hint": hint},
        "reminder_due": engine.compute_reminder_due(data, today, ReminderPrefs()),
    }


async def refresh(
    db: AsyncSession, *, user_id: uuid.UUID
) -> tuple[StreakProfile, StreakState, dict[str, object]]:
    """Recompute streaks from full history and persist the cache row.

    Safe to call any number of times; the pure engine makes replaying
    the same events idempotent.
    """
    settings = get_settings()
    profile = await get_or_create_profile(db, user_id=user_id)
    state = await get_or_create_state(db, user_id=user_id)

    zone = resolve_zone(profile.tz)
    today = datetime.now(UTC).astimezone(zone).date()

    completions = (
        (
            await db.execute(
                select(ScoreEvent.created_at)
                .where(ScoreEvent.user_id == user_id, ScoreEvent.kind == COMPLETION_KIND)
                .order_by(ScoreEvent.created_at.asc())
            )
        )
        .scalars()
        .all()
    )

    freezes: list[date] = [
        row[0]
        for row in (
            await db.execute(
                select(StreakFreeze.freeze_date).order_by(StreakFreeze.freeze_date.asc())
            )
        ).all()
    ]
    if profile.freeze_date is not None:
        freezes.append(profile.freeze_date)

    updated = engine.update_streak(
        _snapshot(state),
        completions,
        today,
        zone,
        profile.weekly_anchor,
        freezes,
        weekly_threshold=settings.streak_weekly_threshold,
    )

    state.current_daily = updated.current_daily
    state.longest_daily = updated.longest_daily
    state.last_completion_date = updated.last_completion_date
    state.current_weekly = updated.current_weekly
    state.longest_weekly = updated.longest_weekly
    state.week_key = updated.week_key
    await db.commit()

    active_days = engine.week_active_days(completions, today, zone, profile.weekly_anchor)
    view = streak_view(
        updated, today=today, active_days=active_days, threshold=settings.streak_weekly_threshold
    )
    return profile, state, view


async def set_preferences(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    tz: str | None = None,
    weekly_anchor: int | None = None,
    reminders_enabled: bool | None = None,
    freeze_date_provided: bool = False,
    freeze_date: date | None = None,
) -> StreakProfile:
    profile = await get_or_create_profile(db, user_id=user_id)
    if tz is not None:
        resolve_zone(tz)  # validate before persisting
        profile.tz = tz
    if weekly_anchor is not None:
        engine.validate_anchor(weekly_anchor)
        profile.weekly_anchor = weekly_anchor
    if reminders_enabled is not None:
        profile.reminders_enabled = reminders_enabled
    if freeze_date_provided:
        profile.freeze_date = freeze_date
    await db.commit()
    return profile


async def add_freeze(
    db: AsyncSession, *, day: date, admin_user_id: uuid.UUID
) -> tuple[StreakFreeze, bool]:
    """Insert one global freeze day; returns ``(freeze, created)``."""
    stmt = (
        pg_insert(StreakFreeze)
        .values(freeze_date=day, created_by=admin_user_id)
        .on_conflict_do_nothing(index_elements=[StreakFreeze.__table__.c.freeze_date])
        .returning(StreakFreeze.freeze_date)
    )
    row = (await db.execute(stmt)).scalar_one_or_none()
    await db.commit()
    if row is None:
        existing = await db.get(StreakFreeze, day)
        assert existing is not None
        return existing, False
    freeze = await db.get(StreakFreeze, row)
    assert freeze is not None
    return freeze, True


__all__ = [
    "COMPLETION_KIND",
    "StreakServiceError",
    "add_freeze",
    "get_or_create_profile",
    "get_or_create_state",
    "refresh",
    "set_preferences",
    "streak_view",
]
