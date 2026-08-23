"""Organization domain tables (plan Phase 11).

Tenancy invariants baked into the schema:
- organizations are addressed by a unique lowercase slug;
- org_members carry the per-org role (owner > instructor > member);
- invite tokens are stored as SHA-256 hashes; plaintext travels once;
- assignment_progress_cache is a lazily refreshed read model derived
  from the learning engine tables and never drives authorization.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from openrange.api.db.base import Base, Timestamped, UUIDPrimaryKey
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column


class Organization(Base, UUIDPrimaryKey, Timestamped):
    __tablename__ = "organizations"
    __table_args__ = (CheckConstraint("name ~ '^[a-z0-9-]{3,40}$'", name="name_format"),)

    name: Mapped[str] = mapped_column(String(40), unique=True)
    display_name: Mapped[str] = mapped_column(String(64), default="")


class OrgMember(Base, UUIDPrimaryKey):
    __tablename__ = "org_members"
    __table_args__ = (
        UniqueConstraint("org_id", "user_id", name="uq_org_members_org_user"),
        CheckConstraint("role IN ('owner', 'instructor', 'member')", name="role_valid"),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    # owner | instructor | member
    role: Mapped[str] = mapped_column(String(16), default="member")
    invited_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Cohort(Base, UUIDPrimaryKey, Timestamped):
    __tablename__ = "cohorts"

    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(64))
    starts_at: Mapped[datetime | None]
    ends_at: Mapped[datetime | None]
    # "metadata" is reserved by SQLAlchemy's declarative API.
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, default=dict)


class CohortMember(Base, UUIDPrimaryKey):
    __tablename__ = "cohort_members"
    __table_args__ = (
        UniqueConstraint("cohort_id", "user_id", name="uq_cohort_members_cohort_user"),
    )

    cohort_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cohorts.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    added_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Assignment(Base, UUIDPrimaryKey, Timestamped):
    __tablename__ = "assignments"
    __table_args__ = (
        CheckConstraint("content_kind IN ('room', 'path')", name="content_kind_valid"),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    # null means the assignment is org-wide
    cohort_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("cohorts.id", ondelete="CASCADE"), index=True
    )
    # room | path
    content_kind: Mapped[str] = mapped_column(String(8))
    content_slug: Mapped[str] = mapped_column(String(128))
    due_at: Mapped[datetime | None]
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )


class AssignmentProgressCache(Base, UUIDPrimaryKey):
    """Lazily refreshed read model over enrollments/section_progress."""

    __tablename__ = "assignment_progress_cache"
    __table_args__ = (
        UniqueConstraint("assignment_id", "user_id", name="uq_assignment_progress_assignment_user"),
        CheckConstraint(
            "status IN ('not_started', 'in_progress', 'completed')", name="status_valid"
        ),
    )

    assignment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("assignments.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(16), default="not_started")
    percent: Mapped[int] = mapped_column(default=0)
    last_event_at: Mapped[datetime | None]


class OrgInvite(Base, UUIDPrimaryKey):
    __tablename__ = "org_invites"

    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    # null means a link invite any authenticated user may accept
    email: Mapped[str | None] = mapped_column(String(320))
    role: Mapped[str] = mapped_column(String(16), default="member")
    expires_at: Mapped[datetime]
    accepted_at: Mapped[datetime | None]
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
