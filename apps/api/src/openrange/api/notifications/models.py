"""Notification domain models: announcements, per-user feed, prefs, email outbox."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from openrange.api.db.base import Base, Timestamped, new_uuid
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column


class Announcement(Base, Timestamped):
    __tablename__ = "announcements"
    __table_args__ = (
        CheckConstraint("severity IN ('info', 'warning', 'critical')", name="severity_valid"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)  # markdown
    severity: Mapped[str] = mapped_column(String(16), default="info")
    audience: Mapped[str] = mapped_column(String(64))  # all | org:<slug> | cohort:<id>
    starts_at: Mapped[datetime]
    ends_at: Mapped[datetime | None]
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )


class NotificationPref(Base, Timestamped):
    __tablename__ = "notification_prefs"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    channel_in_app: Mapped[bool] = mapped_column(Boolean, default=True)
    channel_email: Mapped[bool] = mapped_column(Boolean, default=False)
    digest_weekly: Mapped[bool] = mapped_column(Boolean, default=False)
    muted_categories: Mapped[list[str]] = mapped_column(JSONB, default=list)


class Notification(Base):
    """Materialized per-user feed row.

    Broadcasts are fanned out into one row per recipient at emit time;
    there is deliberately no shared broadcast marker row.
    """

    __tablename__ = "notifications"
    __table_args__ = (
        CheckConstraint(
            "category IN ('lab_expiry', 'announcement', 'achievement', 'assignment', 'system')",
            name="category_valid",
        ),
        Index("ix_notifications_user_created", "user_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    category: Mapped[str] = mapped_column(String(32))
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    read_at: Mapped[datetime | None]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EmailOutbox(Base):
    """Transactional outbox drained by OutboxDrainer every interval.

    next_attempt_at implements retry backoff: failed rows stay queued
    until the timestamp passes, then flip to failed permanently once
    max_attempts is exhausted.
    """

    __tablename__ = "email_outbox"
    __table_args__ = (
        CheckConstraint("status IN ('queued', 'sent', 'failed')", name="status_valid"),
        Index("ix_email_outbox_status_created", "status", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    to_email: Mapped[str] = mapped_column(String(320))
    subject: Mapped[str] = mapped_column(String(500))
    body_text: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="queued")
    attempts: Mapped[int] = mapped_column(default=0)
    last_error: Mapped[str] = mapped_column(Text, default="")
    next_attempt_at: Mapped[datetime | None]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    sent_at: Mapped[datetime | None]
