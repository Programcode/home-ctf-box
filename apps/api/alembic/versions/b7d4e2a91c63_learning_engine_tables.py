"""learning engine tables

Revision ID: b7d4e2a91c63
Revises: 82bfa5281c50
Create Date: 2026-08-23 12:05:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b7d4e2a91c63"
down_revision: str | None = "82bfa5281c50"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "enrollments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("path_slug", sa.String(length=64), nullable=False),
        sa.Column("path_version", sa.String(length=16), nullable=False),
        sa.Column("state", sa.String(length=16), nullable=False),
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
            ["user_id"], ["users.id"], name=op.f("fk_enrollments_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_enrollments")),
    )
    op.create_index(op.f("ix_enrollments_path_slug"), "enrollments", ["path_slug"], unique=False)
    op.create_index(op.f("ix_enrollments_state"), "enrollments", ["state"], unique=False)
    op.create_index(op.f("ix_enrollments_user_id"), "enrollments", ["user_id"], unique=False)
    op.create_index("ix_enrollments_user_state", "enrollments", ["user_id", "state"])
    op.create_index("ix_enrollments_path_state", "enrollments", ["path_slug", "state"])

    op.create_table(
        "section_progress",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("enrollment_id", sa.Uuid(), nullable=False),
        sa.Column("module_slug", sa.String(length=64), nullable=False),
        sa.Column("section_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["enrollment_id"],
            ["enrollments.id"],
            name=op.f("fk_section_progress_enrollment_id_enrollments"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_section_progress")),
        sa.UniqueConstraint(
            "enrollment_id",
            "module_slug",
            "section_id",
            name="uq_section_progress_enrollment_module_section",
        ),
    )
    op.create_index(
        op.f("ix_section_progress_enrollment_id"),
        "section_progress",
        ["enrollment_id"],
        unique=False,
    )
    op.create_index(
        "ix_section_progress_enrollment_module",
        "section_progress",
        ["enrollment_id", "module_slug"],
    )

    op.create_table(
        "quiz_attempts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("enrollment_id", sa.Uuid(), nullable=False),
        sa.Column("section_id", sa.String(length=64), nullable=False),
        sa.Column("module_slug", sa.String(length=64), nullable=False),
        sa.Column("answers", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column(
            "attempted_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["enrollment_id"],
            ["enrollments.id"],
            name=op.f("fk_quiz_attempts_enrollment_id_enrollments"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_quiz_attempts")),
    )
    op.create_index(
        op.f("ix_quiz_attempts_attempted_at"), "quiz_attempts", ["attempted_at"], unique=False
    )
    op.create_index(
        op.f("ix_quiz_attempts_enrollment_id"), "quiz_attempts", ["enrollment_id"], unique=False
    )
    op.create_index(
        "ix_quiz_attempts_enrollment_section", "quiz_attempts", ["enrollment_id", "section_id"]
    )

    op.create_table(
        "notes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("scope", sa.String(length=8), nullable=False),
        sa.Column("ref", sa.String(length=128), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
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
            ["user_id"], ["users.id"], name=op.f("fk_notes_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_notes")),
        sa.UniqueConstraint("user_id", "scope", "ref", name="uq_notes_user_scope_ref"),
    )
    op.create_index(op.f("ix_notes_user_id"), "notes", ["user_id"], unique=False)

    op.create_table(
        "hint_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("enrollment_id", sa.Uuid(), nullable=False),
        sa.Column("task_ref", sa.String(length=64), nullable=False),
        sa.Column("tier", sa.Integer(), nullable=False),
        sa.Column("cost", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["enrollment_id"],
            ["enrollments.id"],
            name=op.f("fk_hint_events_enrollment_id_enrollments"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_hint_events")),
    )
    op.create_index(
        op.f("ix_hint_events_enrollment_id"), "hint_events", ["enrollment_id"], unique=False
    )
    op.create_index("ix_hint_events_enrollment_task", "hint_events", ["enrollment_id", "task_ref"])

    op.create_table(
        "certificates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("path_slug", sa.String(length=64), nullable=False),
        sa.Column("path_version", sa.String(length=16), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "issued_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_certificates_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_certificates")),
        sa.UniqueConstraint("user_id", "path_slug", name="uq_certificates_user_path"),
    )
    op.create_index(op.f("ix_certificates_path_slug"), "certificates", ["path_slug"], unique=False)
    op.create_index(op.f("ix_certificates_user_id"), "certificates", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_certificates_user_id"), table_name="certificates")
    op.drop_index(op.f("ix_certificates_path_slug"), table_name="certificates")
    op.drop_table("certificates")
    op.drop_index("ix_hint_events_enrollment_task", table_name="hint_events")
    op.drop_index(op.f("ix_hint_events_enrollment_id"), table_name="hint_events")
    op.drop_table("hint_events")
    op.drop_index(op.f("ix_notes_user_id"), table_name="notes")
    op.drop_table("notes")
    op.drop_index("ix_quiz_attempts_enrollment_section", table_name="quiz_attempts")
    op.drop_index(op.f("ix_quiz_attempts_enrollment_id"), table_name="quiz_attempts")
    op.drop_index(op.f("ix_quiz_attempts_attempted_at"), table_name="quiz_attempts")
    op.drop_table("quiz_attempts")
    op.drop_index("ix_section_progress_enrollment_module", table_name="section_progress")
    op.drop_index(op.f("ix_section_progress_enrollment_id"), table_name="section_progress")
    op.drop_table("section_progress")
    op.drop_index("ix_enrollments_path_state", table_name="enrollments")
    op.drop_index("ix_enrollments_user_state", table_name="enrollments")
    op.drop_index(op.f("ix_enrollments_user_id"), table_name="enrollments")
    op.drop_index(op.f("ix_enrollments_state"), table_name="enrollments")
    op.drop_index(op.f("ix_enrollments_path_slug"), table_name="enrollments")
    op.drop_table("enrollments")
