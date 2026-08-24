"""Content Studio domain tables (plan Phase 10).

Workflow invariants baked into the schema:
- drafts own an isolated staging directory on disk (content_root);
- reviews are append-only evidence; publish events are append-only audit;
- status transitions live in the service layer so every change is
  accompanied by a publish_events row.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from openrange.api.db.base import Base, Timestamped, UUIDPrimaryKey
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column


class ContentDraft(Base, UUIDPrimaryKey, Timestamped):
    __tablename__ = "drafts"
    __table_args__ = (
        CheckConstraint("kind IN ('room', 'module', 'path')", name="kind_valid"),
        CheckConstraint(
            "status IN ('draft', 'in_review', 'changes_requested', 'approved', 'published')",
            name="status_valid",
        ),
    )

    # room | module | path
    kind: Mapped[str] = mapped_column(String(8))
    slug: Mapped[str] = mapped_column(String(64), index=True)
    base_ref: Mapped[str] = mapped_column(String(256), default="")
    status: Mapped[str] = mapped_column(String(20), default="draft", index=True)
    author_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    # user ids allowed to review besides admins; grows as reviews happen.
    reviewers: Mapped[list[Any]] = mapped_column(JSONB, default=list)
    # absolute path of this draft's workspace dir under STUDIO_CONTENT_ROOT
    content_root: Mapped[str] = mapped_column(Text, default="")


class DraftReview(Base, UUIDPrimaryKey):
    __tablename__ = "draft_reviews"
    __table_args__ = (
        CheckConstraint("state IN ('approved', 'changes_requested')", name="state_valid"),
    )

    draft_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("drafts.id", ondelete="CASCADE"), index=True
    )
    reviewer_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    # approved | changes_requested
    state: Mapped[str] = mapped_column(String(20))
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PublishEvent(Base, UUIDPrimaryKey):
    __tablename__ = "publish_events"
    __table_args__ = (
        CheckConstraint(
            "event IN ('submitted', 'approved', 'published', 'rejected')", name="event_valid"
        ),
    )

    draft_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("drafts.id", ondelete="CASCADE"), index=True
    )
    # submitted | approved | published | rejected
    event: Mapped[str] = mapped_column(String(16))
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    detail: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
