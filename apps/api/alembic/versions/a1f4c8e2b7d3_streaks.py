"""streaks: profiles, states, freeze days

Revision ID: a1f4c8e2b7d3
Revises: d6e1b8f4a2c3
Create Date: 2026-08-24 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a1f4c8e2b7d3"
down_revision: str | None = "d6e1b8f4a2c3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "streak_profiles",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("tz", sa.String(length=64), nullable=False, server_default=sa.text("'UTC'")),
        sa.Column("weekly_anchor", sa.SmallInteger(), nullable=False, server_default=sa.text("0")),
        sa.Column("freeze_date", sa.Date(), nullable=True),
        sa.Column(
            "reminders_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
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
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_streak_profiles_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", name=op.f("pk_streak_profiles")),
        sa.CheckConstraint(
            "weekly_anchor BETWEEN 0 AND 6",
            name=op.f("ck_streak_profiles_anchor_range"),
        ),
    )

    op.create_table(
        "streak_states",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("current_daily", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("longest_daily", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("last_completion_date", sa.Date(), nullable=True),
        sa.Column("current_weekly", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("longest_weekly", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("week_key", sa.String(length=16), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_streak_states_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", name=op.f("pk_streak_states")),
    )

    op.create_table(
        "streak_freezes",
        sa.Column("freeze_date", sa.Date(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name=op.f("fk_streak_freezes_created_by_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("freeze_date", name=op.f("pk_streak_freezes")),
    )


def downgrade() -> None:
    op.drop_table("streak_freezes")
    op.drop_table("streak_states")
    op.drop_table("streak_profiles")
