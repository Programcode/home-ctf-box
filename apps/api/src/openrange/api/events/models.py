"""Event domain tables (plan Phase 9 items 4, 7, 8).

Invariants baked into the schema:
- events are addressed by a unique lowercase slug; visibility is either
  "public" or "org:<slug>" for org-scoped tournaments;
- registrations are polymorphic (kind user|team) with exactly one
  non-null reference and uniqueness per (event, kind, ref);
- event solves carry their subject at insert time. Attribution never
  moves: when a user switches teams mid-event, earlier rows stay with
  the old team and new solves land on the new team;
- the (event, subject, room, task) unique constraint makes ingestion
  idempotent per subject per task;
- event_scoreboards holds the frozen post-freeze snapshot; it is
  written once by the first post-freeze request and only replaced by an
  explicit admin/org-owner refresh.
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


class Event(Base, UUIDPrimaryKey, Timestamped):
    __tablename__ = "events"
    __table_args__ = (
        CheckConstraint("slug ~ '^[a-z0-9-]{3,64}$'", name="slug_format"),
        CheckConstraint("visibility ~ '^(public|org:[a-z0-9-]{3,40})$'", name="visibility_format"),
        CheckConstraint("scoring_model IN ('dynamic', 'static')", name="scoring_model_valid"),
        CheckConstraint("ends_at > starts_at", name="window_valid"),
        CheckConstraint("team_size_max >= team_size_min", name="team_size_valid"),
    )

    slug: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(128))
    starts_at: Mapped[datetime]
    ends_at: Mapped[datetime]
    # After this moment (or ends_at, whichever is earlier) registration
    # closes; NULL means registration runs until the event ends.
    registration_close_at: Mapped[datetime | None]
    # "public" | "org:<org-name>"
    visibility: Mapped[str] = mapped_column(String(48), default="public")
    # dynamic decays points as more solvers arrive; static pays task.points.
    scoring_model: Mapped[str] = mapped_column(String(16), default="static")
    # Decay "start" value in f(n) = base * start / (start + n * decay).
    dynamic_weight: Mapped[int] = mapped_column(default=100)
    team_size_min: Mapped[int] = mapped_column(default=1)
    team_size_max: Mapped[int] = mapped_column(default=4)
    # Once now passes this moment the scoreboard serves its frozen
    # snapshot; NULL means the board stays live for the whole event.
    scoreboard_freeze_at: Mapped[datetime | None]
    # Room slugs allowed in this event.
    content_pool: Mapped[list[str]] = mapped_column(JSONB, default=list)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )


class EventRegistration(Base, UUIDPrimaryKey):
    __tablename__ = "event_registrations"
    __table_args__ = (
        UniqueConstraint(
            "event_id", "kind", "user_id", name="uq_event_registrations_event_kind_user"
        ),
        UniqueConstraint(
            "event_id", "kind", "team_id", name="uq_event_registrations_event_kind_team"
        ),
        CheckConstraint("kind IN ('user', 'team')", name="kind_valid"),
        CheckConstraint("num_nonnulls(user_id, team_id) = 1", name="ref_valid"),
    )

    event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String(8))
    # Exactly one of the two references is set, per ref_valid above.
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    team_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"), index=True
    )
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class EventSolve(Base, UUIDPrimaryKey):
    """One solved task inside an event, attributed at insert time."""

    __tablename__ = "event_solves"
    __table_args__ = (
        UniqueConstraint(
            "event_id",
            "subject_kind",
            "subject_id",
            "room_slug",
            "task_slug",
            name="uq_event_solves_attempt",
        ),
        CheckConstraint("subject_kind IN ('user', 'team')", name="subject_kind_valid"),
    )

    event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), index=True
    )
    subject_kind: Mapped[str] = mapped_column(String(8))
    # Polymorphic pointer to users.id or teams.id. Deliberately not a
    # foreign key: one column must address two tables for the unique
    # attempt constraint to work across both subject kinds.
    subject_id: Mapped[uuid.UUID]
    room_slug: Mapped[str] = mapped_column(String(128))
    task_slug: Mapped[str] = mapped_column(String(128))
    points_awarded: Mapped[int] = mapped_column(default=0)
    first_blood: Mapped[bool] = mapped_column(default=False)
    solved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EventTeamSession(Base, UUIDPrimaryKey):
    """Marks a team as actively competing in an event.

    While a session is active, member solves attribute to that team, but
    only when the solve happens after session start (started_at <=
    solved_at). Ending a session stops future attribution; solves already
    recorded keep their original subject forever.
    """

    __tablename__ = "event_team_sessions"
    __table_args__ = (
        UniqueConstraint("event_id", "team_id", name="uq_event_team_sessions_event_team"),
    )

    event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), index=True
    )
    team_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"), index=True
    )
    active: Mapped[bool] = mapped_column(default=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ended_at: Mapped[datetime | None]


class EventScoreboard(Base, UUIDPrimaryKey):
    """Frozen scoreboard payload served after scoreboard_freeze_at."""

    __tablename__ = "event_scoreboards"

    event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), unique=True, index=True
    )
    payload: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
