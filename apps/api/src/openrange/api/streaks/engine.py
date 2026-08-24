"""Streak engine: pure date math over completion history.

No database, no wall clock: ``today``, the timezone, thresholds, and
freeze days all arrive as arguments, so the same events always produce
the same state and reprocessing is a no-op.

Semantics:
- A completion day is the calendar day of a ``room_solve`` event in the
  user's timezone; several solves on one day count once.
- A missing day breaks the daily chain unless every missing day is
  frozen. Today never breaks the chain: the day is not over.
- Freezes grant continuity only; they never inflate the counter.
- The weekly streak counts anchored weeks with at least
  ``weekly_threshold`` distinct active days. The in-progress week gets
  grace: it can only extend, not break, the run.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

DAILY_MILESTONES: tuple[int, ...] = (3, 7, 14, 30, 60, 100)
DEFAULT_WEEKLY_THRESHOLD = 3


class StreakError(Exception):
    def __init__(self, code: str, status: int = 400) -> None:
        super().__init__(code)
        self.code = code
        self.status = status


@dataclass
class StreakStateData:
    """Serializable snapshot of streak counters."""

    current_daily: int = 0
    longest_daily: int = 0
    last_completion_date: date | None = None
    current_weekly: int = 0
    longest_weekly: int = 0
    week_key: str | None = None


@dataclass
class ReminderPrefs:
    reminders_enabled: bool = True


def _zone(tz: str | ZoneInfo) -> ZoneInfo:
    try:
        return ZoneInfo(tz) if isinstance(tz, str) else tz
    except Exception as exc:
        raise StreakError("invalid_timezone", 422) from exc


def local_date(value: datetime | date, tz: str | ZoneInfo) -> date:
    """Calendar day of ``value`` in ``tz``. Naive datetimes are rejected."""
    if isinstance(value, datetime):
        if value.tzinfo is None:
            raise StreakError("naive datetime is ambiguous", 422)
        return value.astimezone(_zone(tz)).date()
    return value


def validate_anchor(anchor: int) -> int:
    if not 0 <= anchor <= 6:
        raise StreakError("weekly_anchor must be 0-6", 422)
    return anchor


def week_start(day: date, anchor: int) -> date:
    """First day of the user-anchored week containing ``day``."""
    validate_anchor(anchor)
    return day - timedelta(days=(day.weekday() - anchor) % 7)


def week_key(day: date, anchor: int) -> str:
    """ISO year-week label derived from the anchored week start.

    Anchored week starts sit exactly 7 days apart, so each start lands
    in its own ISO year-week and labels never collide.
    """
    iso_year, iso_week, _ = week_start(day, anchor).isocalendar()
    return f"{iso_year}-W{iso_week:02d}"


def _missed_unfrozen(after: date, before: date, freezes: frozenset[date] | set[date]) -> list[date]:
    """Calendar days strictly between ``after`` and ``before`` without freeze."""
    return [
        after + timedelta(days=offset)
        for offset in range(1, (before - after).days)
        if (after + timedelta(days=offset)) not in freezes
    ]


def update_streak(
    state: StreakStateData,
    completion_dates_iterable: Iterable[datetime | date],
    today: date,
    tz: str | ZoneInfo,
    anchor: int,
    freeze_dates: Iterable[date] = (),
    *,
    weekly_threshold: int = DEFAULT_WEEKLY_THRESHOLD,
) -> StreakStateData:
    """Recompute streak counters from full completion history.

    Deterministic and idempotent: identical inputs yield an identical
    result, so replaying the same events (or re-running a refresh)
    changes nothing.
    """
    validate_anchor(anchor)
    if weekly_threshold < 1 or weekly_threshold > 7:
        raise StreakError("weekly threshold must be 1-7", 422)
    freezes = set(freeze_dates)
    days = sorted({local_date(value, tz) for value in completion_dates_iterable})

    # Daily runs: length of the unbroken run ending at each completion.
    run_lengths: list[int] = []
    prev: date | None = None
    for day in days:
        broken = prev is not None and bool(_missed_unfrozen(prev, day, freezes))
        run_lengths.append(1 if broken or prev is None else run_lengths[-1] + 1)
        prev = day

    best_daily = max(run_lengths, default=0)
    alive = bool(days) and not _missed_unfrozen(days[-1], today, freezes)
    current_daily = run_lengths[-1] if alive else 0
    longest_daily = max(state.longest_daily, best_daily)

    # Weekly runs over anchored weeks meeting the active-day threshold.
    counts: dict[str, int] = {}
    starts: dict[str, date] = {}
    for day in days:
        key = week_key(day, anchor)
        counts[key] = counts.get(key, 0) + 1
        starts[key] = week_start(day, anchor)

    run_at: dict[str, int] = {}
    best_weekly = 0
    run = 0
    last_qualifying_start: date | None = None
    for key in sorted(starts, key=lambda k: starts[k]):
        if counts[key] < weekly_threshold:
            continue
        start = starts[key]
        continues = last_qualifying_start is not None and (start - last_qualifying_start).days == 7
        run = run + 1 if continues else 1
        run_at[key] = run
        best_weekly = max(best_weekly, run)
        last_qualifying_start = start

    today_key = week_key(today, anchor)
    current_weekly = run_at.get(today_key, 0)
    if current_weekly == 0:
        # Grace: the in-progress week may still reach the threshold, so
        # a completed previous week keeps the run visible meanwhile.
        previous_key = week_key(week_start(today, anchor) - timedelta(days=7), anchor)
        current_weekly = run_at.get(previous_key, 0)
    longest_weekly = max(state.longest_weekly, best_weekly)

    return StreakStateData(
        current_daily=current_daily,
        longest_daily=longest_daily,
        last_completion_date=days[-1] if days else state.last_completion_date,
        current_weekly=current_weekly,
        longest_weekly=longest_weekly,
        week_key=today_key,
    )


def week_active_days(
    completion_dates_iterable: Iterable[datetime | date],
    today: date,
    tz: str | ZoneInfo,
    anchor: int,
) -> int:
    """Distinct completion days inside today's anchored week."""
    validate_anchor(anchor)
    low = week_start(today, anchor)
    high = low + timedelta(days=6)
    return sum(
        1
        for day in {local_date(value, tz) for value in completion_dates_iterable}
        if low <= day <= high
    )


def next_daily_milestone(current: int) -> int | None:
    for milestone in DAILY_MILESTONES:
        if milestone > current:
            return milestone
    return None


def next_milestone_hint(
    current_daily: int,
    week_active_days_count: int,
    weekly_threshold: int,
    *,
    weekly_streak_alive: bool,
) -> tuple[int | None, str]:
    """Healthily phrased next step. Weekly framing wins while the week
    is unfinished; milestones are invitations, never warnings."""
    remaining_week = weekly_threshold - week_active_days_count
    if weekly_streak_alive and remaining_week > 0:
        unit = "day" if remaining_week == 1 else "days"
        verb = "keeps" if remaining_week == 1 else "keep"
        return None, f"{remaining_week} more {unit} this week {verb} your weekly streak going."
    target = next_daily_milestone(current_daily)
    if target is None:
        return None, "Every solve counts. Explore at your own pace."
    remaining = target - current_daily
    unit = "day" if remaining == 1 else "days"
    return target, f"{remaining} more {unit} reaches your next milestone: {target} days in a row."


def compute_reminder_due(state: StreakStateData, today: date, prefs: ReminderPrefs) -> bool:
    """Whether a gentle nudge is due today.

    Healthy-reminder rules: opt-in only, at most once per day, only to
    protect a live streak, and never about a streak that already broke.
    """
    if not prefs.reminders_enabled or state.current_daily <= 0:
        return False
    last = state.last_completion_date
    return last is not None and last < today
