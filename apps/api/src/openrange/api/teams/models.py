"""Team domain tables.

Invariants baked into the schema:
- team names are unique lowercase slugs matching ^[a-z0-9-]{3,30}$;
- ``team_members.capability`` is the live source of truth for
  authorization; ``teams.captain_id`` records the founding captain and
  is informational once additional captains exist;
- invite codes are stored as SHA-256 hashes; plaintext travels once and
  a code is consumed (set to NULL) on first successful use.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from openrange.api.db.base import Base, Timestamped, UUIDPrimaryKey
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column


class Team(Base, UUIDPrimaryKey, Timestamped):
    __tablename__ = "teams"
    __table_args__ = (CheckConstraint("name ~ '^[a-z0-9-]{3,30}$'", name="name_format"),)

    name: Mapped[str] = mapped_column(String(30), unique=True)
    display_name: Mapped[str] = mapped_column(String(64), default="")
    # Founding captain; day-to-day role checks use team_members.capability.
    captain_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    # Hash of the current single-use join code; NULL means no open invite.
    invite_code_hash: Mapped[str | None] = mapped_column(String(64), unique=True)


class TeamMember(Base, UUIDPrimaryKey):
    __tablename__ = "team_members"
    __table_args__ = (
        UniqueConstraint("team_id", "user_id", name="uq_team_members_team_user"),
        CheckConstraint("capability IN ('member', 'captain')", name="capability_valid"),
    )

    team_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    capability: Mapped[str] = mapped_column(String(16), default="member")
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
