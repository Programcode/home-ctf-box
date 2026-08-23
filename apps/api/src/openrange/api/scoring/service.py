"""Scoring service: ledger ingestion, achievements, leaderboards,
adjustments, and anti-cheat signals (plan Phase 9).

``score_events`` is INSERT-ONLY here. Nothing in this module ever
UPDATEs or DELETEs a score event; corrections are new ``adjustment``
events linked through ``score_adjustments``.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from openrange.api.scoring.models import (
    AchievementCatalog,
    AntiCheatSignal,
    LeaderboardSnapshot,
    ScoreAdjustment,
    ScoreEvent,
    UserAchievement,
)
from openrange.api.scoring.projection import (
    LeaderboardRow,
    MeScore,
    ScoreEventLike,
    leaderboard_row_view,
    project_leaderboard,
    project_me,
)
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

ALLOWED_KINDS: tuple[str, ...] = (
    "room_solve",
    "xp_award",
    "hint_cost",
    "achievement",
    "first_blood",
    "adjustment",
)
SIGNAL_KINDS: frozenset[str] = frozenset(
    {"impossible_timing", "answer_spray", "flag_reuse", "session_mismatch"}
)

# Velocity producer: more than this many room_solve events for one user
# inside the window raises an impossible_timing signal.
VELOCITY_THRESHOLD = 20
VELOCITY_WINDOW = timedelta(seconds=60)


class ScoringError(Exception):
    def __init__(self, code: str, status: int = 400) -> None:
        super().__init__(code)
        self.code = code
        self.status = status


async def record_score_event(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    kind: str,
    ref_slug: str | None = None,
    points: int = 0,
    xp: int = 0,
    meta: dict[str, Any] | None = None,
    idempotency_key: str | None = None,
    created_at: datetime | None = None,
) -> tuple[ScoreEvent, bool]:
    """Insert one ledger event; exactly-once per idempotency_key.

    Returns ``(event, created)``. When the key already exists the
    stored event is returned with ``created=False`` (ON CONFLICT DO
    NOTHING semantics). Post-ingest hooks run only on creation:
    velocity anti-cheat and data-driven achievement evaluation.
    """
    if kind not in ALLOWED_KINDS:
        raise ScoringError(f"unknown score event kind {kind}", 422)
    stmt = (
        pg_insert(ScoreEvent)
        .values(
            user_id=user_id,
            kind=kind,
            ref_slug=ref_slug,
            points=points,
            xp=xp,
            meta=meta or {},
            created_at=created_at or datetime.now(UTC),
            idempotency_key=idempotency_key,
        )
        .on_conflict_do_nothing(index_elements=[ScoreEvent.__table__.c.idempotency_key])
        .returning(ScoreEvent.id)
    )
    row = (await db.execute(stmt)).scalar_one_or_none()
    if row is None:
        existing = await db.scalar(
            select(ScoreEvent).where(ScoreEvent.idempotency_key == idempotency_key)
        )
        assert existing is not None
        return existing, False
    await db.flush()
    event = await db.get(ScoreEvent, row)
    assert event is not None

    if kind == "room_solve":
        await _check_solve_velocity(db, user_id=user_id, at=event.created_at)
    await _evaluate_achievements(db, user_id=user_id)
    return event, True


async def _check_solve_velocity(db: AsyncSession, *, user_id: uuid.UUID, at: datetime) -> None:
    """Flag impossible solve rates regardless of ledger insertion order.

    Every VELOCITY_WINDOW that contains the new event is re-evaluated,
    so backfilled or out-of-order events still trip the threshold.
    """
    stamps = list(
        (
            await db.execute(
                select(ScoreEvent.created_at)
                .where(
                    ScoreEvent.user_id == user_id,
                    ScoreEvent.kind == "room_solve",
                    ScoreEvent.created_at >= at - VELOCITY_WINDOW,
                    ScoreEvent.created_at <= at + VELOCITY_WINDOW,
                )
                .order_by(ScoreEvent.created_at.asc())
            )
        ).scalars()
    )
    observed = 0
    start = 0
    for position, end_at in enumerate(stamps):
        while stamps[start] <= end_at - VELOCITY_WINDOW:
            start += 1
        observed = max(observed, position - start + 1)
    if observed <= VELOCITY_THRESHOLD:
        return
    existing = (
        await db.execute(
            select(AntiCheatSignal.id)
            .where(
                AntiCheatSignal.user_id == user_id,
                AntiCheatSignal.kind == "impossible_timing",
                AntiCheatSignal.status == "open",
            )
            .limit(1)
        )
    ).scalar_one_or_none()
    if existing is None:
        await record_signal(
            db,
            user_id=user_id,
            kind="impossible_timing",
            details={
                "window_seconds": int(VELOCITY_WINDOW.total_seconds()),
                "threshold": VELOCITY_THRESHOLD,
                "observed": int(observed),
            },
        )


async def record_signal(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    kind: str,
    details: dict[str, Any] | None = None,
) -> AntiCheatSignal:
    """Record an anti-cheat signal for later human review."""
    if kind not in SIGNAL_KINDS:
        raise ScoringError(f"unknown signal kind {kind}", 422)
    existing = (
        await db.execute(
            select(AntiCheatSignal)
            .where(
                AntiCheatSignal.user_id == user_id,
                AntiCheatSignal.kind == kind,
                AntiCheatSignal.status == "open",
            )
            .limit(1)
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing
    signal = AntiCheatSignal(user_id=user_id, kind=kind, details=details or {})
    db.add(signal)
    await db.flush()
    return signal


async def review_signal(
    db: AsyncSession,
    *,
    signal_id: int,
    action: str,
    reviewer_id: uuid.UUID,
    note: str,
) -> AntiCheatSignal:
    """Apply a human review decision; signals are never auto-bans."""
    if action not in {"dismiss", "escalate"}:
        raise ScoringError("action must be dismiss or escalate", 422)
    signal = await db.get(AntiCheatSignal, signal_id)
    if signal is None:
        raise ScoringError("unknown signal", 404)
    signal.status = "dismissed" if action == "dismiss" else "escalated"
    signal.review_note = note
    signal.reviewed_by = reviewer_id
    signal.reviewed_at = datetime.now(UTC)
    await db.flush()
    return signal


def validate_achievement_rule(rule: dict[str, Any]) -> None:
    if rule.get("type") != "count":
        raise ScoringError("rule.type must be 'count'", 422)
    if rule.get("event") not in ALLOWED_KINDS:
        raise ScoringError("rule.event must be a known score event kind", 422)
    threshold = rule.get("threshold")
    if not isinstance(threshold, int) or isinstance(threshold, bool) or threshold < 1:
        raise ScoringError("rule.threshold must be a positive integer", 422)
    for field_name in ("points", "xp"):
        value = rule.get(field_name)
        if value is None:
            continue
        if not isinstance(value, int) or isinstance(value, bool):
            raise ScoringError(f"rule.{field_name} must be an integer", 422)


async def upsert_achievement(
    db: AsyncSession,
    *,
    slug: str,
    name: str,
    description: str,
    rule: dict[str, Any],
    active: bool = True,
) -> AchievementCatalog:
    validate_achievement_rule(rule)
    stmt = (
        pg_insert(AchievementCatalog)
        .values(slug=slug, name=name, description=description, rule=rule, active=active)
        .on_conflict_do_update(
            index_elements=[AchievementCatalog.__table__.c.slug],
            set_={"name": name, "description": description, "rule": rule, "active": active},
        )
    )
    await db.execute(stmt)
    await db.flush()
    entry = await db.get(AchievementCatalog, slug)
    assert entry is not None
    return entry


async def list_awarded(db: AsyncSession, *, user_id: uuid.UUID) -> list[dict[str, Any]]:
    rows = (
        await db.execute(
            select(UserAchievement, AchievementCatalog)
            .join(
                AchievementCatalog,
                AchievementCatalog.slug == UserAchievement.slug,
            )
            .where(UserAchievement.user_id == user_id)
            .order_by(UserAchievement.awarded_at.asc())
        )
    ).all()
    return [
        {
            "slug": catalog.slug,
            "name": catalog.name,
            "description": catalog.description,
            "awarded_at": awarded.awarded_at,
        }
        for awarded, catalog in rows
    ]


async def _evaluate_achievements(db: AsyncSession, *, user_id: uuid.UUID) -> None:
    """Award active count-rules the user now qualifies for.

    Each award appends an ``achievement`` ledger event keyed
    ``achv:<slug>:<user>`` so double awards are impossible even across
    races; concurrent evaluators lose the INSERT race harmlessly via
    ON CONFLICT DO NOTHING instead of failing the triggering event.
    """
    rules = (
        (await db.execute(select(AchievementCatalog).where(AchievementCatalog.active)))
        .scalars()
        .all()
    )
    if not rules:
        return
    owned = set(
        (await db.execute(select(UserAchievement.slug).where(UserAchievement.user_id == user_id)))
        .scalars()
        .all()
    )
    for entry in rules:
        if entry.slug in owned:
            continue
        rule = entry.rule
        conditions = [
            ScoreEvent.user_id == user_id,
            ScoreEvent.kind == rule["event"],
        ]
        if rule.get("track"):
            track = str(rule["track"])
            conditions.append(ScoreEvent.meta["track"].astext == track)
        count = (
            await db.execute(select(func.count()).select_from(ScoreEvent).where(*conditions))
        ).scalar_one()
        if int(count) < int(rule["threshold"]):
            continue
        award_stmt = (
            pg_insert(UserAchievement)
            .values(user_id=user_id, slug=entry.slug)
            .on_conflict_do_nothing(index_elements=[UserAchievement.user_id, UserAchievement.slug])
            .returning(UserAchievement.id)
        )
        awarded_id = (await db.execute(award_stmt)).scalar_one_or_none()
        if awarded_id is None:
            continue
        await record_score_event(
            db,
            user_id=user_id,
            kind="achievement",
            ref_slug=entry.slug,
            points=int(rule.get("points", 0)),
            xp=int(rule.get("xp", 0)),
            meta={"achievement": entry.slug},
            idempotency_key=f"achv:{entry.slug}:{user_id}",
        )


async def create_adjustment(
    db: AsyncSession,
    *,
    target_user_id: uuid.UUID,
    points: int,
    reason: str,
    admin_user_id: uuid.UUID,
    original_event_id: int | None = None,
) -> ScoreAdjustment:
    """Append an adjustment event plus its audit linkage.

    Negative ``points`` deduct competitive score; XP is untouched.
    The original event row is never modified.
    """
    if not reason.strip():
        raise ScoringError("reason is required", 422)
    if original_event_id is not None:
        original = await db.get(ScoreEvent, original_event_id)
        if original is None:
            raise ScoringError("unknown original event", 404)
        if original.user_id != target_user_id:
            raise ScoringError("original event belongs to another user", 422)
    adjustment_event, _created = await record_score_event(
        db,
        user_id=target_user_id,
        kind="adjustment",
        points=points,
        meta={"reason": reason, "admin_user_id": str(admin_user_id)},
        idempotency_key=None,
    )
    adjustment = ScoreAdjustment(
        adjustment_event_id=adjustment_event.id,
        original_event_id=original_event_id,
        target_user_id=target_user_id,
        created_by=admin_user_id,
        reason=reason,
    )
    db.add(adjustment)
    await db.flush()
    return adjustment


async def load_events(
    db: AsyncSession,
    *,
    user_id: uuid.UUID | None = None,
    kinds: tuple[str, ...] | None = None,
    ref_slug: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
) -> list[ScoreEventLike]:
    stmt = select(ScoreEvent).order_by(ScoreEvent.created_at.asc(), ScoreEvent.id.asc())
    if user_id is not None:
        stmt = stmt.where(ScoreEvent.user_id == user_id)
    if kinds is not None:
        stmt = stmt.where(ScoreEvent.kind.in_(kinds))
    if ref_slug is not None:
        stmt = stmt.where(ScoreEvent.ref_slug == ref_slug)
    if since is not None:
        stmt = stmt.where(ScoreEvent.created_at >= since)
    if until is not None:
        stmt = stmt.where(ScoreEvent.created_at < until)
    rows: list[ScoreEventLike] = list((await db.execute(stmt)).scalars().all())
    return rows


def period_window(period: str) -> tuple[datetime, datetime]:
    """UTC month window for a YYYY-MM key; raises on malformed input."""
    try:
        start = datetime.strptime(period, "%Y-%m").replace(tzinfo=UTC)
    except ValueError as exc:
        raise ScoringError("period must be YYYY-MM", 422) from exc
    if start.month == 12:
        next_year, next_month = start.year + 1, 1
    else:
        next_year, next_month = start.year, start.month + 1
    end = start.replace(year=next_year, month=next_month)
    return start, end


async def compute_leaderboard(
    db: AsyncSession,
    *,
    scope: str,
    period_key: str,
    ref_slug: str | None = None,
    metric: str = "points",
    since: datetime | None = None,
    until: datetime | None = None,
    kinds: tuple[str, ...] | None = None,
) -> list[LeaderboardRow]:
    """Project events into ranked rows and freeze a snapshot.

    Deterministic and replayable: recomputing for the same ledger state
    produces identical rows regardless of prior snapshots.
    """
    events = await load_events(db, kinds=kinds, ref_slug=ref_slug, since=since, until=until)
    rows = project_leaderboard(events, metric=metric)
    payload = [leaderboard_row_view(r) for r in rows]
    snapshot_stmt = (
        pg_insert(LeaderboardSnapshot)
        .values(scope=scope, period_key=period_key, payload=payload)
        .on_conflict_do_update(
            index_elements=[
                LeaderboardSnapshot.__table__.c.scope,
                LeaderboardSnapshot.__table__.c.period_key,
            ],
            set_={"payload": payload, "computed_at": datetime.now(UTC)},
        )
    )
    await db.execute(snapshot_stmt)
    await db.flush()
    return rows


async def me_score(db: AsyncSession, *, user_id: uuid.UUID) -> MeScore:
    events = await load_events(db, user_id=user_id)
    return project_me(events, user_id)
