"""jeopardy challenges

Revision ID: d6e1b8f4a2c3
Revises: f3a9c2e47b81
Create Date: 2026-08-24 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d6e1b8f4a2c3"
down_revision: str | None = "d8e1f4a6b2c7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "challenges",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("category", sa.String(length=16), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("difficulty", sa.Integer(), nullable=False),
        sa.Column("points_base", sa.Integer(), nullable=False),
        sa.Column("scoring", sa.String(length=8), nullable=False),
        sa.Column("dynamic_decay", postgresql.JSONB(), nullable=True),
        sa.Column("flag_hash", sa.String(length=64), nullable=False),
        sa.Column("flag_case_sensitive", sa.Boolean(), nullable=False),
        sa.Column("state", sa.String(length=8), nullable=False),
        sa.Column(
            "author_id",
            sa.Uuid(),
            nullable=False,
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
            ["author_id"],
            ["users.id"],
            name=op.f("fk_challenges_author_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_challenges")),
        sa.UniqueConstraint("slug", name=op.f("uq_challenges_slug")),
        sa.CheckConstraint(
            "category IN ('web', 'crypto', 'pwn', 'rev', 'forensics', 'misc', 'osint')",
            name=op.f("ck_challenges_category_valid"),
        ),
        sa.CheckConstraint(
            "scoring IN ('static', 'dynamic')",
            name=op.f("ck_challenges_scoring_valid"),
        ),
        sa.CheckConstraint(
            "state IN ('hidden', 'visible')",
            name=op.f("ck_challenges_state_valid"),
        ),
        sa.CheckConstraint(
            "difficulty BETWEEN 1 AND 10",
            name=op.f("ck_challenges_difficulty_range"),
        ),
    )
    op.create_index(op.f("ix_challenges_slug"), "challenges", ["slug"], unique=True)
    op.create_index(op.f("ix_challenges_author_id"), "challenges", ["author_id"], unique=False)
    op.create_index(op.f("ix_challenges_state"), "challenges", ["state"], unique=False)

    op.create_table(
        "challenge_files",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("challenge_id", sa.Uuid(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("size", sa.BigInteger(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["challenge_id"],
            ["challenges.id"],
            name=op.f("fk_challenge_files_challenge_id_challenges"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_challenge_files")),
        sa.UniqueConstraint("storage_path", name=op.f("uq_challenge_files_storage_path")),
    )
    op.create_index(
        op.f("ix_challenge_files_challenge_id"),
        "challenge_files",
        ["challenge_id"],
        unique=False,
    )

    op.create_table(
        "challenge_solves",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("challenge_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "submitted_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["challenge_id"],
            ["challenges.id"],
            name=op.f("fk_challenge_solves_challenge_id_challenges"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_challenge_solves_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_challenge_solves")),
        sa.UniqueConstraint(
            "challenge_id",
            "user_id",
            name=op.f("uq_challenge_solves_challenge_user"),
        ),
    )
    op.create_index(
        op.f("ix_challenge_solves_challenge_id"),
        "challenge_solves",
        ["challenge_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_challenge_solves_user_id"), "challenge_solves", ["user_id"], unique=False
    )

    op.create_table(
        "challenge_submissions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("challenge_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("submission_norm", sa.Text(), nullable=False),
        sa.Column("correct", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["challenge_id"],
            ["challenges.id"],
            name=op.f("fk_challenge_submissions_challenge_id_challenges"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_challenge_submissions_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_challenge_submissions")),
    )
    op.create_index(
        op.f("ix_challenge_submissions_challenge_id"),
        "challenge_submissions",
        ["challenge_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_challenge_submissions_user_id"),
        "challenge_submissions",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_challenge_submissions_created_at"),
        "challenge_submissions",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("challenge_submissions")
    op.drop_table("challenge_solves")
    op.drop_table("challenge_files")
    op.drop_index(op.f("ix_challenges_state"), table_name="challenges")
    op.drop_index(op.f("ix_challenges_author_id"), table_name="challenges")
    op.drop_index(op.f("ix_challenges_slug"), table_name="challenges")
    op.drop_table("challenges")
