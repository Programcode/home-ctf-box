"""Notifications core service: audience resolution, emit fanout, views."""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from openrange.api.notifications.models import EmailOutbox, Notification, NotificationPref
from openrange.api.users.models import User
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

CATEGORIES = ("lab_expiry", "announcement", "achievement", "assignment", "system")


async def resolve_audience(db: AsyncSession, audience: str) -> list[uuid.UUID]:
    """Resolve an audience expression to user ids at emit time.

    ``all`` covers every non-deleted account. ``org:<slug>`` and
    ``cohort:<id>`` resolvers land with the Phase 11 tables; until those
    models exist in this branch they fan out to nobody.
    """
    if audience == "all":
        rows = await db.execute(select(User.id).where(User.deleted_at.is_(None)))
        return list(rows.scalars())
    logger.info("audience %r has no resolver yet; zero recipients", audience[:64])
    return []


def _email_fields(category: str, payload: dict[str, Any]) -> tuple[str, str]:
    subject = str(payload.get("title") or f"[OpenRange] {category}")[:500]
    body = payload.get("message") or payload.get("body") or json.dumps(payload, default=str)
    return subject, str(body)


async def emit(
    db: AsyncSession,
    *,
    category: str,
    payload: dict[str, Any],
    user_ids: list[uuid.UUID] | set[uuid.UUID] | None = None,
    audience: str | None = None,
) -> list[Notification]:
    """Fan out one materialized notification row per recipient.

    Honors preferences: muted categories are skipped entirely; in-app is
    on by default; email requires an explicit opt-in pref plus an email
    address on file and enqueues into email_outbox for the drainer.
    """
    if category not in CATEGORIES:
        raise ValueError(f"unknown notification category {category!r}")
    requested = {uid for uid in (user_ids or [])}
    if audience is not None:
        requested.update(await resolve_audience(db, audience))
    if not requested:
        return []

    rows = (
        (await db.execute(select(User).where(User.id.in_(requested), User.deleted_at.is_(None))))
        .scalars()
        .all()
    )
    recipients = {u.id: u for u in rows}

    prefs: dict[uuid.UUID, NotificationPref] = {}
    if recipients:
        pref_rows = (
            (
                await db.execute(
                    select(NotificationPref).where(NotificationPref.user_id.in_(recipients))
                )
            )
            .scalars()
            .all()
        )
        prefs = {p.user_id: p for p in pref_rows}

    created: list[Notification] = []
    for uid, user in recipients.items():
        pref = prefs.get(uid)
        if category in (pref.muted_categories if pref else []):
            continue
        if pref is None or pref.channel_in_app:
            notification = Notification(user_id=uid, category=category, payload=payload)
            db.add(notification)
            created.append(notification)
        wants_email = bool(pref.channel_email) if pref else False
        if wants_email and user.email:
            subject, body = _email_fields(category, payload)
            db.add(EmailOutbox(to_email=user.email, subject=subject, body_text=body))
    await db.flush()
    return created


def notification_view(n: Notification) -> dict[str, Any]:
    return {
        "id": str(n.id),
        "category": n.category,
        "payload": n.payload,
        "read_at": n.read_at.isoformat() if n.read_at else None,
        "created_at": n.created_at.isoformat(),
    }


def announcement_view(a: Any) -> dict[str, Any]:
    return {
        "id": str(a.id),
        "title": a.title,
        "body": a.body,
        "severity": a.severity,
        "audience": a.audience,
        "starts_at": a.starts_at.isoformat(),
        "ends_at": a.ends_at.isoformat() if a.ends_at else None,
        "created_by": str(a.created_by) if a.created_by else None,
        "created_at": a.created_at.isoformat(),
    }
