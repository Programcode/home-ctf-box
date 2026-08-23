"""scoring engine core

Revision ID: c4d9e2f81b70
Revises: 82bfa5281c50
Create Date: 2026-08-23 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "c4d9e2f81b70"
down_revision: str | None = "b7d4e2a91c63"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "score_events",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("ref_slug", sa.String(length=64), nullable=True),
        sa.Column("points", sa.Integer(), nullable=False),
        sa.Column("xp", sa.Integer(), nullable=False),
        sa.Column("meta", JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("idempotency_key", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_score_events_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_score_events")),
        sa.UniqueConstraint("idempotency_key", name=op.f("uq_score_events_idempotency_key")),
    )
    op.create_index(
        "ix_score_events_user_kind_created",
        "score_events",
        ["user_id", "kind", "created_at"],
        unique=False,
    )
    op.create_index(op.f("ix_score_events_user_id"), "score_events", ["user_id"], unique=False)
    op.create_index(op.f("ix_score_events_ref_slug"), "score_events", ["ref_slug"], unique=False)
    op.create_index(
        op.f("ix_score_events_created_at"), "score_events", ["created_at"], unique=False
    )
    op.create_table(
        "score_adjustments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("adjustment_event_id", sa.BigInteger(), nullable=False),
        sa.Column("original_event_id", sa.BigInteger(), nullable=True),
        sa.Column("target_user_id", sa.Uuid(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["adjustment_event_id"],
            ["score_events.id"],
            name=op.f("fk_score_adjustments_adjustment_event_id_score_events"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["original_event_id"],
            ["score_events.id"],
            name=op.f("fk_score_adjustments_original_event_id_score_events"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["target_user_id"],
            ["users.id"],
            name=op.f("fk_score_adjustments_target_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name=op.f("fk_score_adjustments_created_by_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_score_adjustments")),
    )
    op.create_index(
        op.f("ix_score_adjustments_adjustment_event_id"),
        "score_adjustments",
        ["adjustment_event_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_score_adjustments_original_event_id"),
        "score_adjustments",
        ["original_event_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_score_adjustments_target_user_id"),
        "score_adjustments",
        ["target_user_id"],
        unique=False,
    )
    op.create_table(
        "achievements_catalog",
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("rule", JSONB(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("slug", name=op.f("pk_achievements_catalog")),
    )
    op.create_table(
        "user_achievements",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column(
            "awarded_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_user_achievements_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["slug"],
            ["achievements_catalog.slug"],
            name=op.f("fk_user_achievements_slug_achievements_catalog"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_achievements")),
        sa.UniqueConstraint("user_id", "slug", name="uq_user_achievements_user_slug"),
    )
    op.create_index(
        op.f("ix_user_achievements_user_id"), "user_achievements", ["user_id"], unique=False
    )
    op.create_table(
        "leaderboard_snapshots",
        sa.Column("scope", sa.String(length=16), nullable=False),
        sa.Column("period_key", sa.String(length=64), nullable=False),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column(
            "computed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("scope", "period_key", name=op.f("pk_leaderboard_snapshots")),
    )
    op.create_table(
        "anti_cheat_signals",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("details", JSONB(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("review_note", sa.Text(), nullable=False),
        sa.Column("reviewed_by", sa.Uuid(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_anti_cheat_signals_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by"],
            ["users.id"],
            name=op.f("fk_anti_cheat_signals_reviewed_by_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_anti_cheat_signals")),
    )
    op.create_index(
        op.f("ix_anti_cheat_signals_user_id"), "anti_cheat_signals", ["user_id"], unique=False
    )
    op.create_index(
        op.f("ix_anti_cheat_signals_status"), "anti_cheat_signals", ["status"], unique=False
    )
    op.create_index(
        op.f("ix_anti_cheat_signals_created_at"), "anti_cheat_signals", ["created_at"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_anti_cheat_signals_created_at"), table_name="anti_cheat_signals")
    op.drop_index(op.f("ix_anti_cheat_signals_status"), table_name="anti_cheat_signals")
    op.drop_index(op.f("ix_anti_cheat_signals_user_id"), table_name="anti_cheat_signals")
    op.drop_table("anti_cheat_signals")
    op.drop_table("leaderboard_snapshots")
    op.drop_index(op.f("ix_user_achievements_user_id"), table_name="user_achievements")
    op.drop_table("user_achievements")
    op.drop_table("achievements_catalog")
    op.drop_index(op.f("ix_score_adjustments_target_user_id"), table_name="score_adjustments")
    op.drop_index(op.f("ix_score_adjustments_original_event_id"), table_name="score_adjustments")
    op.drop_index(op.f("ix_score_adjustments_adjustment_event_id"), table_name="score_adjustments")
    op.drop_table("score_adjustments")
    op.drop_index(op.f("ix_score_events_created_at"), table_name="score_events")
    op.drop_index(op.f("ix_score_events_ref_slug"), table_name="score_events")
    op.drop_index(op.f("ix_score_events_user_id"), table_name="score_events")
    op.drop_index("ix_score_events_user_kind_created", table_name="score_events")
    op.drop_table("score_events")
