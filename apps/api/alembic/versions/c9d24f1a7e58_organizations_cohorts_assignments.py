"""organizations, cohorts, assignments, org invites

Revision ID: c9d24f1a7e58
Revises: b7d4e2a91c63
Create Date: 2026-08-23 14:10:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c9d24f1a7e58"
down_revision: str | None = "c4d9e2f81b70"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=40), nullable=False),
        sa.Column("display_name", sa.String(length=64), nullable=False),
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
        sa.CheckConstraint("name ~ '^[a-z0-9-]{3,40}$'", name="ck_organizations_name_format"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_organizations")),
        sa.UniqueConstraint("name", name=op.f("uq_organizations_name")),
    )

    op.create_table(
        "org_members",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("org_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("invited_by", sa.Uuid(), nullable=True),
        sa.Column(
            "joined_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["invited_by"],
            ["users.id"],
            name=op.f("fk_org_members_invited_by_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["org_id"],
            ["organizations.id"],
            name=op.f("fk_org_members_org_id_organizations"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_org_members_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "role IN ('owner', 'instructor', 'member')", name="ck_org_members_role_valid"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_org_members")),
        sa.UniqueConstraint("org_id", "user_id", name="uq_org_members_org_user"),
    )
    op.create_index(op.f("ix_org_members_org_id"), "org_members", ["org_id"], unique=False)
    op.create_index(op.f("ix_org_members_user_id"), "org_members", ["user_id"], unique=False)

    op.create_table(
        "cohorts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("org_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
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
            ["org_id"],
            ["organizations.id"],
            name=op.f("fk_cohorts_org_id_organizations"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_cohorts")),
    )
    op.create_index(op.f("ix_cohorts_org_id"), "cohorts", ["org_id"], unique=False)

    op.create_table(
        "cohort_members",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("cohort_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("added_by", sa.Uuid(), nullable=True),
        sa.Column(
            "joined_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["added_by"],
            ["users.id"],
            name=op.f("fk_cohort_members_added_by_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["cohort_id"],
            ["cohorts.id"],
            name=op.f("fk_cohort_members_cohort_id_cohorts"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_cohort_members_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_cohort_members")),
        sa.UniqueConstraint("cohort_id", "user_id", name="uq_cohort_members_cohort_user"),
    )
    op.create_index(op.f("ix_cohort_members_cohort_id"), "cohort_members", ["cohort_id"])
    op.create_index(op.f("ix_cohort_members_user_id"), "cohort_members", ["user_id"])

    op.create_table(
        "assignments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("org_id", sa.Uuid(), nullable=False),
        sa.Column("cohort_id", sa.Uuid(), nullable=True),
        sa.Column("content_kind", sa.String(length=8), nullable=False),
        sa.Column("content_slug", sa.String(length=128), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["cohort_id"],
            ["cohorts.id"],
            name=op.f("fk_assignments_cohort_id_cohorts"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name=op.f("fk_assignments_created_by_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["org_id"],
            ["organizations.id"],
            name=op.f("fk_assignments_org_id_organizations"),
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "content_kind IN ('room', 'path')", name="ck_assignments_content_kind_valid"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_assignments")),
    )
    op.create_index(op.f("ix_assignments_cohort_id"), "assignments", ["cohort_id"])
    op.create_index(op.f("ix_assignments_org_id"), "assignments", ["org_id"])

    op.create_table(
        "assignment_progress_cache",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("assignment_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("percent", sa.Integer(), nullable=False),
        sa.Column("last_event_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["assignment_id"],
            ["assignments.id"],
            name=op.f("fk_assignment_progress_cache_assignment_id_assignments"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_assignment_progress_cache_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "status IN ('not_started', 'in_progress', 'completed')",
            name="ck_assignment_progress_cache_status_valid",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_assignment_progress_cache")),
        sa.UniqueConstraint(
            "assignment_id", "user_id", name="uq_assignment_progress_assignment_user"
        ),
    )
    op.create_index(
        op.f("ix_assignment_progress_cache_assignment_id"),
        "assignment_progress_cache",
        ["assignment_id"],
    )
    op.create_index(
        op.f("ix_assignment_progress_cache_user_id"), "assignment_progress_cache", ["user_id"]
    )

    op.create_table(
        "org_invites",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("org_id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
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
            name=op.f("fk_org_invites_created_by_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["org_id"],
            ["organizations.id"],
            name=op.f("fk_org_invites_org_id_organizations"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_org_invites")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_org_invites_token_hash")),
    )
    op.create_index(op.f("ix_org_invites_org_id"), "org_invites", ["org_id"], unique=False)
    op.create_index(op.f("ix_org_invites_token_hash"), "org_invites", ["token_hash"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_org_invites_token_hash"), table_name="org_invites")
    op.drop_index(op.f("ix_org_invites_org_id"), table_name="org_invites")
    op.drop_table("org_invites")
    op.drop_index(
        op.f("ix_assignment_progress_cache_user_id"), table_name="assignment_progress_cache"
    )
    op.drop_index(
        op.f("ix_assignment_progress_cache_assignment_id"), table_name="assignment_progress_cache"
    )
    op.drop_table("assignment_progress_cache")
    op.drop_index(op.f("ix_assignments_org_id"), table_name="assignments")
    op.drop_index(op.f("ix_assignments_cohort_id"), table_name="assignments")
    op.drop_table("assignments")
    op.drop_index(op.f("ix_cohort_members_user_id"), table_name="cohort_members")
    op.drop_index(op.f("ix_cohort_members_cohort_id"), table_name="cohort_members")
    op.drop_table("cohort_members")
    op.drop_index(op.f("ix_cohorts_org_id"), table_name="cohorts")
    op.drop_table("cohorts")
    op.drop_index(op.f("ix_org_members_user_id"), table_name="org_members")
    op.drop_index(op.f("ix_org_members_org_id"), table_name="org_members")
    op.drop_table("org_members")
    op.drop_table("organizations")
