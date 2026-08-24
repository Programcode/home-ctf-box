"""content studio: drafts, reviews, publish events

Revision ID: b3e8a5d7c1f9
Revises: e4b7c9d2a1f6
Create Date: 2026-08-23 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b3e8a5d7c1f9"
down_revision: str | None = "e4b7c9d2a1f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "drafts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=8), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("base_ref", sa.String(length=256), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("author_id", sa.Uuid(), nullable=False),
        sa.Column("reviewers", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("content_root", sa.Text(), nullable=False),
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
            ["author_id"], ["users.id"], name=op.f("fk_drafts_author_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_drafts")),
        sa.CheckConstraint("kind IN ('room', 'module', 'path')", name=op.f("ck_drafts_kind_valid")),
        sa.CheckConstraint(
            "status IN ('draft', 'in_review', 'changes_requested', 'approved', 'published')",
            name=op.f("ck_drafts_status_valid"),
        ),
    )
    op.create_index(op.f("ix_drafts_author_id"), "drafts", ["author_id"], unique=False)
    op.create_index(op.f("ix_drafts_slug"), "drafts", ["slug"], unique=False)
    op.create_index(op.f("ix_drafts_status"), "drafts", ["status"], unique=False)

    op.create_table(
        "draft_reviews",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("draft_id", sa.Uuid(), nullable=False),
        sa.Column("reviewer_id", sa.Uuid(), nullable=True),
        sa.Column("state", sa.String(length=20), nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["draft_id"],
            ["drafts.id"],
            name=op.f("fk_draft_reviews_draft_id_drafts"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["reviewer_id"],
            ["users.id"],
            name=op.f("fk_draft_reviews_reviewer_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_draft_reviews")),
        sa.CheckConstraint(
            "state IN ('approved', 'changes_requested')", name=op.f("ck_draft_reviews_state_valid")
        ),
    )
    op.create_index(op.f("ix_draft_reviews_draft_id"), "draft_reviews", ["draft_id"], unique=False)

    op.create_table(
        "publish_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("draft_id", sa.Uuid(), nullable=False),
        sa.Column("event", sa.String(length=16), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=True),
        sa.Column("detail", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["actor_id"],
            ["users.id"],
            name=op.f("fk_publish_events_actor_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["draft_id"],
            ["drafts.id"],
            name=op.f("fk_publish_events_draft_id_drafts"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_publish_events")),
        sa.CheckConstraint(
            "event IN ('submitted', 'approved', 'published', 'rejected')",
            name=op.f("ck_publish_events_event_valid"),
        ),
    )
    op.create_index(
        op.f("ix_publish_events_draft_id"), "publish_events", ["draft_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_publish_events_draft_id"), table_name="publish_events")
    op.drop_table("publish_events")
    op.drop_index(op.f("ix_draft_reviews_draft_id"), table_name="draft_reviews")
    op.drop_table("draft_reviews")
    op.drop_index(op.f("ix_drafts_status"), table_name="drafts")
    op.drop_index(op.f("ix_drafts_slug"), table_name="drafts")
    op.drop_index(op.f("ix_drafts_author_id"), table_name="drafts")
    op.drop_table("drafts")
