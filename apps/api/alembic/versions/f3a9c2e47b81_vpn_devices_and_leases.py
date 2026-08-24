"""vpn devices and leases

Revision ID: f3a9c2e47b81
Revises: b3e8a5d7c1f9
Create Date: 2026-08-24 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f3a9c2e47b81"
down_revision: str | None = "b3e8a5d7c1f9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "vpn_devices",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=32), nullable=False),
        sa.Column("public_key", sa.Text(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_vpn_devices_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_vpn_devices")),
        sa.UniqueConstraint("public_key", name=op.f("uq_vpn_devices_public_key")),
        sa.CheckConstraint(
            "char_length(name) BETWEEN 1 AND 32",
            name=op.f("ck_vpn_devices_name_length"),
        ),
    )

    op.create_table(
        "vpn_leases",
        sa.Column("device_id", sa.Uuid(), nullable=False),
        sa.Column("address", postgresql.INET(), nullable=False),
        sa.Column(
            "allocated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["device_id"],
            ["vpn_devices.id"],
            name=op.f("fk_vpn_leases_device_id_vpn_devices"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("device_id", name=op.f("pk_vpn_leases")),
        sa.UniqueConstraint("address", name=op.f("uq_vpn_leases_address")),
    )


def downgrade() -> None:
    op.drop_table("vpn_leases")
    op.drop_table("vpn_devices")
