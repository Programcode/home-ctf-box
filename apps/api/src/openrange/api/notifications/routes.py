"""Notification HTTP routes: /api/notifications.

The outbox drainer is a small worker loop owned by this module; its
start/stop hooks ride on the router's on_startup/on_shutdown so main.py
only needs the include line.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated, Any, Literal, cast

from fastapi import APIRouter, Query
from openrange.api.auth.dependencies import CurrentUser, DbSession
from openrange.api.auth.service import AuthError
from openrange.api.notifications import service as notifsvc
from openrange.api.notifications.email import sender_from_settings
from openrange.api.notifications.models import (
    Announcement,
    EmailOutbox,
    Notification,
    NotificationPref,
)
from openrange.api.notifications.service import notification_view
from openrange.api.notifications.worker import OutboxDrainer
from pydantic import BaseModel, Field
from sqlalchemy import func, select, update
from sqlalchemy.engine import CursorResult

Category = Literal["lab_expiry", "announcement", "achievement", "assignment", "system"]
Severity = Literal["info", "warning", "critical"]

drainer = OutboxDrainer()


async def _start_drainer() -> None:
    drainer.sender = sender_from_settings()
    await drainer.start()


async def _stop_drainer() -> None:
    await drainer.stop()


router = APIRouter(
    prefix="/api/notifications",
    tags=["notifications"],
    on_startup=[_start_drainer],
    on_shutdown=[_stop_drainer],
)


class PrefsIn(BaseModel):
    channel_in_app: bool = True
    channel_email: bool = False
    digest_weekly: bool = False
    muted_categories: list[Category] = []


def _prefs_view(p: NotificationPref) -> dict[str, object]:
    return {
        "channel_in_app": p.channel_in_app,
        "channel_email": p.channel_email,
        "digest_weekly": p.digest_weekly,
        "muted_categories": list(p.muted_categories),
    }


async def _load_prefs(db: DbSession, user_id: uuid.UUID) -> NotificationPref:
    pref = await db.get(NotificationPref, user_id)
    if pref is None:
        pref = NotificationPref(user_id=user_id)
        db.add(pref)
        await db.flush()
    return pref


@router.get("/me")
async def my_feed(
    user: CurrentUser,
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, object]:
    total = (
        await db.execute(
            select(func.count()).select_from(Notification).where(Notification.user_id == user.id)
        )
    ).scalar_one()
    # Unread first, newest first within each group; the composite index
    # (user_id, created_at) serves both orderings.
    rows = (
        (
            await db.execute(
                select(Notification)
                .where(Notification.user_id == user.id)
                .order_by(
                    Notification.read_at.is_not(None).asc(),
                    Notification.created_at.desc(),
                )
                .limit(limit)
                .offset(offset)
            )
        )
        .scalars()
        .all()
    )
    return {"items": [notification_view(n) for n in rows], "total": int(total), "offset": offset}


@router.post("/{notification_id}/read")
async def mark_read(notification_id: str, user: CurrentUser, db: DbSession) -> dict[str, object]:
    nid = _parse_or_404(notification_id)
    row = await db.get(Notification, nid)
    if row is None or row.user_id != user.id:
        raise AuthError("unknown notification", 404)
    if row.read_at is None:
        row.read_at = datetime.now(UTC)
    return {"id": str(row.id), "read": True}


@router.post("/read-all")
async def read_all(user: CurrentUser, db: DbSession) -> dict[str, object]:
    result = cast(
        CursorResult[Any],
        await db.execute(
            update(Notification)
            .where(
                Notification.user_id == user.id,
                Notification.read_at.is_(None),
            )
            .values(read_at=datetime.now(UTC))
        ),
    )
    return {"updated": int(result.rowcount or 0)}


@router.get("/me/prefs")
async def get_prefs(user: CurrentUser, db: DbSession) -> dict[str, object]:
    return _prefs_view(await _load_prefs(db, user.id))


@router.put("/me/prefs")
async def put_prefs(payload: PrefsIn, user: CurrentUser, db: DbSession) -> dict[str, object]:
    pref = await _load_prefs(db, user.id)
    pref.channel_in_app = payload.channel_in_app
    pref.channel_email = payload.channel_email
    pref.digest_weekly = payload.digest_weekly
    pref.muted_categories = list(payload.muted_categories)
    return _prefs_view(pref)


class AnnouncementIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1)
    severity: Severity = "info"
    audience: str = Field(default="all", pattern=r"^(all|org:[^\s:]+|cohort:[^\s:]+)$")
    starts_at: datetime | None = None
    ends_at: datetime | None = None


async def _require(user: CurrentUser, permission: str) -> None:
    if not user.has_permission(permission):
        raise AuthError(f"missing permission {permission}", 403)


@router.post("/admin/announcements")
async def create_announcement(
    payload: AnnouncementIn, user: CurrentUser, db: DbSession
) -> dict[str, object]:
    await _require(user, "settings:write")
    announcement = Announcement(
        title=payload.title,
        body=payload.body,
        severity=payload.severity,
        audience=payload.audience,
        starts_at=payload.starts_at or datetime.now(UTC),
        ends_at=payload.ends_at,
        created_by=user.id,
    )
    db.add(announcement)
    await db.flush()
    if announcement.starts_at <= datetime.now(UTC):
        await notifsvc.emit(
            db,
            category="announcement",
            audience=announcement.audience,
            payload={
                "announcement_id": str(announcement.id),
                "title": announcement.title,
                "severity": announcement.severity,
                "body": announcement.body,
            },
        )
    return notifsvc.announcement_view(announcement)


@router.get("/admin/announcements")
async def list_announcements(
    user: CurrentUser,
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
) -> list[dict[str, object]]:
    await _require(user, "settings:write")
    rows = (
        (
            await db.execute(
                select(Announcement).order_by(Announcement.created_at.desc()).limit(limit)
            )
        )
        .scalars()
        .all()
    )
    return [notifsvc.announcement_view(a) for a in rows]


@router.delete("/admin/announcements/{announcement_id}")
async def delete_announcement(
    announcement_id: str, user: CurrentUser, db: DbSession
) -> dict[str, bool]:
    await _require(user, "settings:write")
    aid = _parse_or_404(announcement_id)
    row = await db.get(Announcement, aid)
    if row is None:
        raise AuthError("unknown announcement", 404)
    await db.delete(row)
    return {"deleted": True}


@router.get("/admin/email-outbox")
async def email_outbox(
    user: CurrentUser,
    db: DbSession,
    status: Literal["queued", "sent", "failed"] | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
) -> list[dict[str, object]]:
    # Ops visibility into the drain loop; guarded by system:operate.
    await _require(user, "system:operate")
    stmt = select(EmailOutbox).order_by(EmailOutbox.created_at.desc()).limit(limit)
    if status is not None:
        stmt = stmt.where(EmailOutbox.status == status)
    rows = (await db.execute(stmt)).scalars().all()

    def view(r: EmailOutbox) -> dict[str, object]:
        return {
            "id": str(r.id),
            "to_email": r.to_email,
            "subject": r.subject,
            "status": r.status,
            "attempts": r.attempts,
            "last_error": r.last_error,
            "next_attempt_at": r.next_attempt_at.isoformat() if r.next_attempt_at else None,
            "created_at": r.created_at.isoformat(),
            "sent_at": r.sent_at.isoformat() if r.sent_at else None,
        }

    return [view(r) for r in rows]


def _parse_or_404(raw: str) -> uuid.UUID:
    try:
        return uuid.UUID(raw)
    except ValueError as exc:
        raise AuthError("unknown id", 404) from exc
