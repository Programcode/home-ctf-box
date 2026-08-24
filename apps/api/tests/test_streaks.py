"""Streaks gate (plan Phase 9 item 5).

Pure-engine properties: timezone-safe completion days, same-day dedup,
freeze bridging exactly once, weekly threshold edges, monotonic healthy
hints, gentle-reminder rules, idempotent reprocessing. Integration:
RBAC negatives plus an end-to-end refresh over real score_events.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, date, datetime, timedelta
from typing import Any

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration

STRONG = "correct-horse-battery"

_clients: list[AsyncClient] = []


@pytest.fixture(autouse=True)
async def _close_clients() -> AsyncIterator[None]:
    yield
    while _clients:
        await _clients.pop().aclose()


async def _make_user(username: str) -> tuple[AsyncClient, dict[str, str], uuid.UUID]:
    """Isolated client per user so cookie jars never collide."""
    from httpx import ASGITransport
    from openrange.api.main import create_app

    app = create_app()
    client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test", timeout=120)
    _clients.append(client)
    res = await client.post("/api/auth/register", json={"username": username, "password": STRONG})
    assert res.status_code == 201, res.text
    headers = {"x-csrf-token": res.json()["csrf_token"]}
    me = await client.get("/api/users/me")
    assert me.status_code == 200
    return client, headers, uuid.UUID(me.json()["id"])


async def _make_admin(username: str) -> tuple[AsyncClient, dict[str, str], uuid.UUID]:
    from openrange.api.auth.service import grant_role
    from openrange.api.users.models import User
    from sqlalchemy import select

    client, headers, user_id = await _make_user(username)
    async with _db() as db:
        user = (await db.execute(select(User).where(User.id == user_id))).scalar_one()
        await grant_role(db, user, "admin")
        await db.commit()
    return client, headers, user_id


@asynccontextmanager
async def _db() -> AsyncIterator[Any]:
    from openrange.api.db import session_factory as sf

    assert sf is not None
    async with sf() as session:
        yield session


def _streak(
    events: list[datetime | date],
    today: date,
    *,
    anchor: int = 0,
    freezes: list[date] | tuple[date, ...] = (),
    tz: str = "UTC",
    threshold: int = 3,
) -> Any:
    from openrange.api.streaks.engine import StreakStateData, update_streak

    return update_streak(
        StreakStateData(),
        events,
        today,
        tz,
        anchor,
        freezes,
        weekly_threshold=threshold,
    )


def _dt(*args: int) -> datetime:
    return datetime(*args, tzinfo=UTC)


# ---------------------------------------------------------------- pure engine


def test_same_local_day_completions_count_once() -> None:
    state = _streak(
        [_dt(2026, 8, 20, 9, 0), _dt(2026, 8, 20, 18, 30), _dt(2026, 8, 20, 23, 59)],
        date(2026, 8, 20),
    )
    assert state.current_daily == 1
    assert state.last_completion_date == date(2026, 8, 20)


def test_tz_boundary_2330_utc_maps_to_different_days() -> None:
    instant = _dt(2026, 8, 20, 23, 30)
    utc = _streak([instant], date(2026, 8, 21))
    assert utc.last_completion_date == date(2026, 8, 20)
    kiritimati = _streak([instant], date(2026, 8, 21), tz="Pacific/Kiritimati")
    assert kiritimati.last_completion_date == date(2026, 8, 21)
    new_york = _streak([instant], date(2026, 8, 21), tz="America/New_York")
    assert new_york.last_completion_date == date(2026, 8, 20)


def test_tz_boundary_merges_or_splits_chains() -> None:
    # 23:30Z and 00:30Z next day are consecutive UTC days but one local
    # evening in Budapest (UTC+2 in August).
    events = [_dt(2026, 8, 20, 23, 30), _dt(2026, 8, 21, 0, 30)]
    utc_chain = _streak(events, date(2026, 8, 21))
    assert utc_chain.current_daily == 2
    budapest = _streak(events, date(2026, 8, 21), tz="Europe/Budapest")
    # Both instants are the same Budapest evening (UTC+2 in August).
    assert budapest.current_daily == 1
    assert budapest.last_completion_date == date(2026, 8, 21)


def test_gap_resets_and_freeze_preserves_chain_exactly_once() -> None:
    monday, wednesday = date(2026, 8, 17), date(2026, 8, 19)
    tuesday = date(2026, 8, 18)

    broken = _streak([monday, wednesday], wednesday)
    assert broken.current_daily == 1
    assert broken.longest_daily == 1

    frozen = _streak([monday, wednesday], wednesday, freezes=(tuesday,))
    # Freeze grants continuity only; Tuesday itself never inflates.
    assert frozen.current_daily == 2
    assert frozen.longest_daily == 2

    replay = _streak([monday, wednesday], wednesday, freezes=(tuesday, tuesday))
    assert replay == frozen

    again = _streak([monday, wednesday], wednesday, freezes=(tuesday,))
    assert again == frozen


def test_one_freeze_bridges_one_missing_day_only() -> None:
    monday, thursday = date(2026, 8, 17), date(2026, 8, 20)
    one = _streak([monday, thursday], thursday, freezes=(date(2026, 8, 18),))
    assert one.current_daily == 1
    two = _streak([monday, thursday], thursday, freezes=(date(2026, 8, 18), date(2026, 8, 19)))
    assert two.current_daily == 2


def test_today_grace_then_break_then_freeze_saves() -> None:
    today = date(2026, 8, 21)
    assert _streak([today - timedelta(days=1)], today).current_daily == 1
    assert _streak([today - timedelta(days=2)], today).current_daily == 0
    saved = _streak([today - timedelta(days=2)], today, freezes=(today - timedelta(days=1),))
    assert saved.current_daily == 1


def test_weekly_threshold_edge_two_vs_three_active_days() -> None:
    from openrange.api.streaks.engine import week_active_days

    today = date(2026, 8, 21)  # Friday of the Mon 2026-08-17 week
    two = [date(2026, 8, 17), date(2026, 8, 19)]
    three = [*two, date(2026, 8, 20)]

    low = _streak(two, today)
    assert low.current_weekly == 0
    assert week_active_days(two, today, "UTC", 0) == 2

    high = _streak(three, today)
    assert high.current_weekly == 1
    assert week_active_days(three, today, "UTC", 0) == 3

    stricter = _streak(three, today, threshold=5)
    assert stricter.current_weekly == 0


def test_weekly_run_survives_across_qualifying_weeks_and_grace() -> None:
    # Prior week (Mon Aug 10) qualified; this week is unfinished Friday.
    prior = [date(2026, 8, 10), date(2026, 8, 11), date(2026, 8, 13)]
    this_week_so_far = [date(2026, 8, 21)]
    state = _streak(prior + this_week_so_far, date(2026, 8, 21))
    assert state.current_weekly == 1  # grace keeps prior run visible
    assert state.week_key.startswith("2026-W")

    # Completing this week extends the run instead of resetting it.
    completed = _streak(
        [*prior, date(2026, 8, 21), date(2026, 8, 22), date(2026, 8, 23)], date(2026, 8, 23)
    )
    assert completed.current_weekly == 2
    assert completed.longest_weekly == 2


def test_milestone_hints_are_monotonic_and_positive() -> None:
    from openrange.api.streaks.engine import DAILY_MILESTONES, next_milestone_hint

    top = DAILY_MILESTONES[-1]
    last_target = 0
    seen_targets: list[int] = []
    for current in range(0, top + 2):
        target, hint = next_milestone_hint(
            current, week_active_days_count=99, weekly_threshold=3, weekly_streak_alive=False
        )
        if target is None:
            assert current >= top
            continue
        assert target > current
        assert target >= last_target
        assert f"{target - current} more" in hint
        if not seen_targets or seen_targets[-1] != target:
            seen_targets.append(target)
        last_target = target
    assert seen_targets == list(DAILY_MILESTONES)


def test_weekly_hint_counts_down_within_the_week() -> None:
    from openrange.api.streaks.engine import next_milestone_hint

    hints = [
        next_milestone_hint(
            5, week_active_days_count=n, weekly_threshold=3, weekly_streak_alive=True
        )[1]
        for n in range(0, 4)
    ]
    assert hints[0].startswith("3 more days this week")
    assert hints[1].startswith("2 more days this week")
    assert hints[2].startswith("1 more day this week")
    # Week satisfied: fall back to the daily milestone invitation.
    assert "milestone" in hints[3]


def test_reminder_due_is_gentle_and_opt_in() -> None:
    from openrange.api.streaks.engine import (
        ReminderPrefs,
        StreakStateData,
        compute_reminder_due,
    )

    today = date(2026, 8, 21)
    alive = StreakStateData(current_daily=3, last_completion_date=today - timedelta(days=1))
    assert compute_reminder_due(alive, today, ReminderPrefs()) is True
    done_today = StreakStateData(current_daily=3, last_completion_date=today)
    assert compute_reminder_due(done_today, today, ReminderPrefs()) is False
    opted_out = StreakStateData(current_daily=3, last_completion_date=today - timedelta(days=1))
    assert compute_reminder_due(opted_out, today, ReminderPrefs(reminders_enabled=False)) is False
    dead = StreakStateData(current_daily=0, last_completion_date=None)
    assert compute_reminder_due(dead, today, ReminderPrefs()) is False


def test_reprocessing_same_events_is_idempotent() -> None:
    events = [_dt(2026, 8, 17, 10, 0), _dt(2026, 8, 19, 22, 0), _dt(2026, 8, 19, 23, 30)]
    first = _streak(events, date(2026, 8, 20))
    second = _streak(events, date(2026, 8, 20))
    third = _streak([*events, *events], date(2026, 8, 20))
    assert first == second == third


# ------------------------------------------------------------- integration


async def test_anonymous_cannot_read_streaks(client: Any) -> None:
    res = await client.get("/api/streaks/me")
    assert res.status_code == 401


async def test_non_admin_cannot_create_freeze() -> None:
    client, headers, _uid = await _make_user("streakpleb")
    res = await client.post("/api/streaks/freeze", json={"date": "2026-12-25"}, headers=headers)
    assert res.status_code == 403


async def test_me_flow_refresh_is_idempotent(db_engine: Any) -> None:
    from openrange.api.scoring.service import record_score_event

    _client, headers, uid = await _make_user("streaker")
    now = datetime.now(UTC)
    async with _db() as db:
        await record_score_event(
            db,
            user_id=uid,
            kind="room_solve",
            ref_slug="room-a",
            points=100,
            xp=10,
            created_at=now - timedelta(days=1),
            idempotency_key=f"streak-test:{uid}:room-a",
        )
        # record_score_event flushes only; make it visible to the app's
        # own request-scoped sessions.
        await db.commit()

    first = await _client_get(headers)
    assert first["daily"]["current"] == 1
    assert first["daily"]["longest"] == 1
    assert first["daily"]["last_completion_date"] == (now.date() - timedelta(days=1)).isoformat()
    assert first["reminder_due"] is True
    assert first["weekly"]["week_progress"]["active_days"] >= 0

    second = await _client_get(headers)
    assert second == first


async def _client_get(headers: dict[str, str]) -> dict[str, Any]:
    client = _clients[-1]
    res = await client.get("/api/streaks/me", headers=headers)
    assert res.status_code == 200, res.text
    return res.json()


async def test_preferences_validation_and_persistence(db_engine: Any) -> None:
    client, headers, _uid = await _make_user("streakprefs")

    bad_tz = await client.post(
        "/api/streaks/me/preferences", json={"tz": "Mars/Olympus"}, headers=headers
    )
    assert bad_tz.status_code == 422

    bad_anchor = await client.post(
        "/api/streaks/me/preferences", json={"weekly_anchor": 7}, headers=headers
    )
    assert bad_anchor.status_code == 422

    ok = await client.post(
        "/api/streaks/me/preferences",
        json={
            "tz": "Europe/Budapest",
            "weekly_anchor": 6,
            "reminders_enabled": False,
            "freeze_date": "2026-12-24",
        },
        headers=headers,
    )
    assert ok.status_code == 200, ok.text
    body = ok.json()
    assert body["tz"] == "Europe/Budapest"
    assert body["weekly_anchor"] == 6
    assert body["reminders_enabled"] is False
    assert body["freeze_date"] == "2026-12-24"

    cleared = await client.post(
        "/api/streaks/me/preferences", json={"freeze_date": None}, headers=headers
    )
    assert cleared.status_code == 200
    assert cleared.json()["freeze_date"] is None


async def test_admin_freeze_is_idempotent(db_engine: Any) -> None:
    from openrange.api.streaks.models import StreakFreeze
    from sqlalchemy import func, select

    client, headers, _admin_id = await _make_admin("streakadmin")

    first = await client.post("/api/streaks/freeze", json={"date": "2026-12-25"}, headers=headers)
    assert first.status_code == 200, first.text
    assert first.json()["created"] is True

    second = await client.post("/api/streaks/freeze", json={"date": "2026-12-25"}, headers=headers)
    assert second.status_code == 200
    assert second.json()["created"] is False

    async with _db() as db:
        count = (
            await db.execute(
                select(func.count())
                .select_from(StreakFreeze)
                .where(StreakFreeze.freeze_date == date(2026, 12, 25))
            )
        ).scalar_one()
    assert count == 1
