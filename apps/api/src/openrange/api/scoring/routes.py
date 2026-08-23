"""Scoring HTTP routes: /api/scoring."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Query
from openrange.api.auth.dependencies import CurrentUser, DbSession, require_permission
from openrange.api.auth.service import AuthError
from openrange.api.scoring import service
from openrange.api.scoring.models import AntiCheatSignal
from openrange.api.scoring.projection import LeaderboardRow
from openrange.api.users.models import User
from pydantic import BaseModel, Field
from sqlalchemy import select

router = APIRouter(prefix="/api/scoring", tags=["scoring"])

# Admin scoring operations ride the settings:write permission: admins hold
# every permission, no other role does, so no rbac.py change is needed.
AdminUser = Annotated[User, Depends(require_permission("settings:write"))]


class AchievementIn(BaseModel):
    slug: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=128)
    description: str = ""
    rule: dict[str, Any]
    active: bool = True


class ScoreAdjustmentIn(BaseModel):
    user_id: uuid.UUID
    points: int
    reason: str = Field(min_length=1)
    original_event_id: int | None = None


class SignalReviewIn(BaseModel):
    action: Literal["dismiss", "escalate"]
    note: str = ""


def _row_view(row: LeaderboardRow) -> dict[str, Any]:
    return {
        "rank": row.rank,
        "user_id": str(row.user_id),
        "points": row.points,
        "xp": row.xp,
        "event_count": row.event_count,
        "last_event_at": row.last_event_at.isoformat() if row.last_event_at else None,
        "first_bloods": row.first_bloods,
    }


def _window(period: str | None) -> tuple[datetime | None, datetime | None]:
    """(since, until) for an optional YYYY-MM filter; UTC months."""
    if not period:
        return None, None
    start, end = service.period_window(period)
    return start, end


@router.get("/me/score")
async def my_score(user: CurrentUser, db: DbSession) -> dict[str, Any]:
    score = await service.me_score(db, user_id=user.id)
    return {
        "user_id": str(score.user_id),
        "points": score.points,
        "xp": score.xp,
        "event_count": score.event_count,
        "tracks": score.tracks,
        "first_bloods": list(score.first_blood_refs),
    }


@router.get("/me/achievements")
async def my_achievements(user: CurrentUser, db: DbSession) -> list[dict[str, Any]]:
    awarded = await service.list_awarded(db, user_id=user.id)
    return [
        {
            "slug": entry["slug"],
            "name": entry["name"],
            "description": entry["description"],
            "awarded_at": entry["awarded_at"].isoformat(),
        }
        for entry in awarded
    ]


@router.get("/leaderboards/{scope}")
async def leaderboard(
    scope: Literal["all_time", "monthly", "seasonal"],
    db: DbSession,
    user: CurrentUser,
    period: Annotated[str | None, Query()] = None,
) -> dict[str, Any]:
    if scope == "all_time":
        period_key, since, until = "all", None, None
    elif scope == "monthly":
        if not period:
            raise AuthError("monthly leaderboards require period=YYYY-MM", 422)
        start, end = service.period_window(period)
        period_key, since, until = period, start, end
    else:
        # seasonal: period_key is an opaque season slug; season date
        # windows arrive with the seasons feature (tables exist today).
        if not period:
            raise AuthError("seasonal leaderboards require period=<season-slug>", 422)
        period_key, since, until = period, None, None
    rows = await service.compute_leaderboard(
        db, scope=scope, period_key=period_key, since=since, until=until
    )
    return {"scope": scope, "period_key": period_key, "rows": [_row_view(r) for r in rows]}


@router.get("/leaderboards/{scope}/{ref}")
async def ref_board(
    scope: Literal["room", "path"],
    ref: str,
    db: DbSession,
    user: CurrentUser,
    period: Annotated[str | None, Query()] = None,
) -> dict[str, Any]:
    """Room boards rank competitive points; path boards rank XP."""
    since, until = _window(period)
    metric = "points" if scope == "room" else "xp"
    kinds = ("room_solve", "first_blood") if scope == "room" else ("xp_award", "hint_cost")
    period_key = f"{ref}@{period}" if period else ref
    rows = await service.compute_leaderboard(
        db,
        scope=scope,
        period_key=period_key,
        ref_slug=ref,
        metric=metric,
        since=since,
        until=until,
        kinds=kinds,
    )
    return {"scope": scope, "ref": ref, "rows": [_row_view(r) for r in rows]}


@router.post("/admin/achievements")
async def upsert_achievement(
    payload: AchievementIn, admin: AdminUser, db: DbSession
) -> dict[str, Any]:
    try:
        entry = await service.upsert_achievement(
            db,
            slug=payload.slug,
            name=payload.name,
            description=payload.description,
            rule=payload.rule,
            active=payload.active,
        )
    except service.ScoringError as exc:
        raise AuthError(exc.code, exc.status) from exc
    return {
        "slug": entry.slug,
        "name": entry.name,
        "description": entry.description,
        "rule": entry.rule,
        "active": entry.active,
    }


@router.post("/admin/score-adjustments")
async def create_adjustment(
    payload: ScoreAdjustmentIn, admin: AdminUser, db: DbSession
) -> dict[str, Any]:
    try:
        adjustment = await service.create_adjustment(
            db,
            target_user_id=payload.user_id,
            points=payload.points,
            reason=payload.reason,
            admin_user_id=admin.id,
            original_event_id=payload.original_event_id,
        )
    except service.ScoringError as exc:
        raise AuthError(exc.code, exc.status) from exc
    return {
        "id": adjustment.adjustment_event_id,
        "original_event_id": adjustment.original_event_id,
        "target_user_id": str(adjustment.target_user_id),
        "reason": adjustment.reason,
    }


@router.get("/admin/anti-cheat/signals")
async def list_signals(
    admin: AdminUser,
    db: DbSession,
    status: Annotated[Literal["open", "dismissed", "escalated"] | None, Query()] = "open",
) -> list[dict[str, Any]]:
    stmt = select(AntiCheatSignal).order_by(AntiCheatSignal.created_at.desc()).limit(200)
    if status is not None:
        stmt = stmt.where(AntiCheatSignal.status == status)
    rows = (await db.execute(stmt)).scalars().all()
    return [
        {
            "id": signal.id,
            "user_id": str(signal.user_id),
            "kind": signal.kind,
            "status": signal.status,
            "details": signal.details,
            "review_note": signal.review_note,
            "reviewed_by": str(signal.reviewed_by) if signal.reviewed_by else None,
            "reviewed_at": signal.reviewed_at.isoformat() if signal.reviewed_at else None,
            "created_at": signal.created_at.isoformat(),
        }
        for signal in rows
    ]


@router.post("/admin/anti-cheat/signals/{signal_id}/review")
async def review_signal(
    signal_id: int,
    payload: SignalReviewIn,
    admin: AdminUser,
    db: DbSession,
) -> dict[str, Any]:
    try:
        signal = await service.review_signal(
            db,
            signal_id=signal_id,
            action=payload.action,
            reviewer_id=admin.id,
            note=payload.note,
        )
    except service.ScoringError as exc:
        raise AuthError(exc.code, exc.status) from exc
    return {
        "id": signal.id,
        "status": signal.status,
        "review_note": signal.review_note,
        "reviewed_at": signal.reviewed_at.isoformat() if signal.reviewed_at else None,
    }
