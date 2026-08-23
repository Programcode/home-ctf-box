"""Learning engine tables: enrollments, section progress, quiz attempts,
notes, hint events, and certificates."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from openrange.api.db.base import Base, Timestamped, new_uuid
from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column


class Enrollment(Base, Timestamped):
    __tablename__ = "enrollments"
    __table_args__ = (
        Index("ix_enrollments_user_state", "user_id", "state"),
        Index("ix_enrollments_path_state", "path_slug", "state"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    path_slug: Mapped[str] = mapped_column(String(64), index=True)
    path_version: Mapped[str] = mapped_column(String(16), default="")
    # active | paused | completed
    state: Mapped[str] = mapped_column(String(16), default="active")


class SectionProgress(Base):
    """One row per completed (enrollment, module, section) triple."""

    __tablename__ = "section_progress"
    __table_args__ = (
        UniqueConstraint(
            "enrollment_id",
            "module_slug",
            "section_id",
            name="uq_section_progress_enrollment_module_section",
        ),
        Index("ix_section_progress_enrollment_module", "enrollment_id", "module_slug"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    enrollment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("enrollments.id", ondelete="CASCADE"), index=True
    )
    module_slug: Mapped[str] = mapped_column(String(64))
    section_id: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16), default="completed")
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class QuizAttempt(Base):
    """Server-graded quiz attempt; answer keys never leave the bundle."""

    __tablename__ = "quiz_attempts"
    __table_args__ = (Index("ix_quiz_attempts_enrollment_section", "enrollment_id", "section_id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    enrollment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("enrollments.id", ondelete="CASCADE"), index=True
    )
    section_id: Mapped[str] = mapped_column(String(64))
    module_slug: Mapped[str] = mapped_column(String(64))
    answers: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    passed: Mapped[bool] = mapped_column(default=False)
    attempted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


class Note(Base, Timestamped):
    """Autosaved markdown note scoped to a room or module reference."""

    __tablename__ = "notes"
    __table_args__ = (UniqueConstraint("user_id", "scope", "ref", name="uq_notes_user_scope_ref"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    scope: Mapped[str] = mapped_column(String(8))  # room | module
    ref: Mapped[str] = mapped_column(String(128))
    body: Mapped[str] = mapped_column(Text, default="")


class HintEvent(Base):
    """Append-only progressive-hint reveal ledger with its XP-safe cost."""

    __tablename__ = "hint_events"
    __table_args__ = (Index("ix_hint_events_enrollment_task", "enrollment_id", "task_ref"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    enrollment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("enrollments.id", ondelete="CASCADE"), index=True
    )
    task_ref: Mapped[str] = mapped_column(String(64))
    tier: Mapped[int] = mapped_column(default=1)
    cost: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Certificate(Base):
    """Verifiable completion certificate; payload carries the signed
    evidence hash over the canonical progress snapshot."""

    __tablename__ = "certificates"
    __table_args__ = (UniqueConstraint("user_id", "path_slug", name="uq_certificates_user_path"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    path_slug: Mapped[str] = mapped_column(String(64), index=True)
    path_version: Mapped[str] = mapped_column(String(16))
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
