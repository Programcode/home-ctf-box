"""teams, events builder, frozen scoreboards

Revision ID: d8e1f4a6b2c7
Revises: f3a9c2e47b81
Create Date: 2026-08-24 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "d8e1f4a6b2c7"
down_revision: str | None = "f3a9c2e47b81"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "teams",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=30), nullable=False),
        sa.Column("display_name", sa.String(length=64), nullable=False),
        sa.Column("captain_id", sa.Uuid(), nullable=True),
        sa.Column("invite_code_hash", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("name ~ '^[a-z0-9-]{3,30}$'", name=op.f("ck_teams_name_format")),
        sa.ForeignKeyConstraint(
            ["captain_id"],
            ["users.id"],
            name=op.f("fk_teams_captain_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_teams")),
        sa.UniqueConstraint("invite_code_hash", name=op.f("uq_teams_invite_code_hash")),
        sa.UniqueConstraint("name", name=op.f("uq_teams_name")),
    )
    op.create_index(op.f("ix_teams_captain_id"), "teams", ["captain_id"], unique=False)
    op.create_table(
        "team_members",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("team_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("capability", sa.String(length=16), nullable=False),
        sa.Column(
            "joined_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "capability IN ('member', 'captain')",
            name=op.f("ck_team_members_capability_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["team_id"],
            ["teams.id"],
            name=op.f("fk_team_members_team_id_teams"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_team_members_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_team_members")),
        sa.UniqueConstraint("team_id", "user_id", name="uq_team_members_team_user"),
    )
    op.create_index(op.f("ix_team_members_team_id"), "team_members", ["team_id"], unique=False)
    op.create_index(op.f("ix_team_members_user_id"), "team_members", ["user_id"], unique=False)
    op.create_table(
        "events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("registration_close_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("visibility", sa.String(length=48), nullable=False),
        sa.Column("scoring_model", sa.String(length=16), nullable=False),
        sa.Column("dynamic_weight", sa.Integer(), nullable=False),
        sa.Column("team_size_min", sa.Integer(), nullable=False),
        sa.Column("team_size_max", sa.Integer(), nullable=False),
        sa.Column("scoreboard_freeze_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("content_pool", JSONB(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("ends_at > starts_at", name=op.f("ck_events_window_valid")),
        sa.CheckConstraint(
            "scoring_model IN ('dynamic', 'static')",
            name=op.f("ck_events_scoring_model_valid"),
        ),
        sa.CheckConstraint("slug ~ '^[a-z0-9-]{3,64}$'", name=op.f("ck_events_slug_format")),
        sa.CheckConstraint(
            "team_size_max >= team_size_min", name=op.f("ck_events_team_size_valid")
        ),
        sa.CheckConstraint(
            "visibility ~ '^(public|org:[a-z0-9-]{3,40})$'",
            name=op.f("ck_events_visibility_format"),
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name=op.f("fk_events_created_by_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_events")),
        sa.UniqueConstraint("slug", name=op.f("uq_events_slug")),
    )
    op.create_index(op.f("ix_events_created_by"), "events", ["created_by"], unique=False)
    op.create_table(
        "event_registrations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=8), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("team_id", sa.Uuid(), nullable=True),
        sa.Column(
            "registered_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "kind IN ('user', 'team')", name=op.f("ck_event_registrations_kind_valid")
        ),
        sa.CheckConstraint(
            "num_nonnulls(user_id, team_id) = 1",
            name=op.f("ck_event_registrations_ref_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["event_id"],
            ["events.id"],
            name=op.f("fk_event_registrations_event_id_events"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["team_id"],
            ["teams.id"],
            name=op.f("fk_event_registrations_team_id_teams"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_event_registrations_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_event_registrations")),
        sa.UniqueConstraint(
            "event_id", "kind", "user_id", name="uq_event_registrations_event_kind_user"
        ),
        sa.UniqueConstraint(
            "event_id", "kind", "team_id", name="uq_event_registrations_event_kind_team"
        ),
    )
    op.create_index(
        op.f("ix_event_registrations_event_id"),
        "event_registrations",
        ["event_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_event_registrations_team_id"),
        "event_registrations",
        ["team_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_event_registrations_user_id"),
        "event_registrations",
        ["user_id"],
        unique=False,
    )
    op.create_table(
        "event_solves",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("subject_kind", sa.String(length=8), nullable=False),
        sa.Column("subject_id", sa.Uuid(), nullable=False),
        sa.Column("room_slug", sa.String(length=128), nullable=False),
        sa.Column("task_slug", sa.String(length=128), nullable=False),
        sa.Column("points_awarded", sa.Integer(), nullable=False),
        sa.Column("first_blood", sa.Boolean(), nullable=False),
        sa.Column(
            "solved_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "subject_kind IN ('user', 'team')", name=op.f("ck_event_solves_subject_kind_valid")
        ),
        sa.ForeignKeyConstraint(
            ["event_id"],
            ["events.id"],
            name=op.f("fk_event_solves_event_id_events"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_event_solves")),
        sa.UniqueConstraint(
            "event_id",
            "subject_kind",
            "subject_id",
            "room_slug",
            "task_slug",
            name="uq_event_solves_attempt",
        ),
    )
    op.create_index(op.f("ix_event_solves_event_id"), "event_solves", ["event_id"], unique=False)
    op.create_table(
        "event_team_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("team_id", sa.Uuid(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["event_id"],
            ["events.id"],
            name=op.f("fk_event_team_sessions_event_id_events"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["team_id"],
            ["teams.id"],
            name=op.f("fk_event_team_sessions_team_id_teams"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_event_team_sessions")),
        sa.UniqueConstraint("event_id", "team_id", name="uq_event_team_sessions_event_team"),
    )
    op.create_index(
        op.f("ix_event_team_sessions_event_id"),
        "event_team_sessions",
        ["event_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_event_team_sessions_team_id"),
        "event_team_sessions",
        ["team_id"],
        unique=False,
    )
    op.create_table(
        "event_scoreboards",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column(
            "computed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["event_id"],
            ["events.id"],
            name=op.f("fk_event_scoreboards_event_id_events"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_event_scoreboards")),
        sa.UniqueConstraint("event_id", name=op.f("uq_event_scoreboards_event_id")),
    )
    op.create_index(
        op.f("ix_event_scoreboards_event_id"),
        "event_scoreboards",
        ["event_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_event_scoreboards_event_id"), table_name="event_scoreboards")
    op.drop_table("event_scoreboards")
    op.drop_index(op.f("ix_event_team_sessions_team_id"), table_name="event_team_sessions")
    op.drop_index(op.f("ix_event_team_sessions_event_id"), table_name="event_team_sessions")
    op.drop_table("event_team_sessions")
    op.drop_index(op.f("ix_event_solves_event_id"), table_name="event_solves")
    op.drop_table("event_solves")
    op.drop_index(op.f("ix_event_registrations_user_id"), table_name="event_registrations")
    op.drop_index(op.f("ix_event_registrations_team_id"), table_name="event_registrations")
    op.drop_index(op.f("ix_event_registrations_event_id"), table_name="event_registrations")
    op.drop_table("event_registrations")
    op.drop_index(op.f("ix_events_created_by"), table_name="events")
    op.drop_table("events")
    op.drop_index(op.f("ix_team_members_user_id"), table_name="team_members")
    op.drop_index(op.f("ix_team_members_team_id"), table_name="team_members")
    op.drop_table("team_members")
    op.drop_index(op.f("ix_teams_captain_id"), table_name="teams")
    op.drop_table("teams")
