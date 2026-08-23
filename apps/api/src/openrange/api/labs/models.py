"""Runtime models: lab instances, lifecycle events, cleanup jobs."""

from __future__ import annotations

import uuid
from datetime import datetime

from openrange.api.db.base import Base, Timestamped, new_uuid
from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column


class LabInstance(Base):
    __tablename__ = "lab_instances"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    room_slug: Mapped[str] = mapped_column(String(64), index=True)
    content_version: Mapped[str] = mapped_column(String(16))
    state: Mapped[str] = mapped_column(String(24), default="requested", index=True)
    runner_instance_id: Mapped[uuid.UUID | None]
    network_name: Mapped[str] = mapped_column(String(64), default="")
    targets_json: Mapped[str] = mapped_column(Text, default="{}")
    flags_json: Mapped[str] = mapped_column(Text, default="{}")
    ttl_minutes: Mapped[int] = mapped_column(default=90)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    stopped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failure_reason: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (Index("ix_lab_instances_user_state", "user_id", "state"),)


class RuntimeEvent(Base):
    """Append-only lifecycle audit trail per instance."""

    __tablename__ = "runtime_events"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    instance_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("lab_instances.id", ondelete="CASCADE"), index=True
    )
    event: Mapped[str] = mapped_column(String(32))
    detail: Mapped[str] = mapped_column(Text, default="")
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class CleanupJob(Base, Timestamped):
    __tablename__ = "cleanup_jobs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    instance_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("lab_instances.id", ondelete="CASCADE"), index=True
    )
    reason: Mapped[str] = mapped_column(String(32))  # expired | user-stop | reconcile
    attempts: Mapped[int] = mapped_column(default=0)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
