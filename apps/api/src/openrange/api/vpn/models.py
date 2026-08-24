"""VPN domain models: registered devices and their address leases."""

from __future__ import annotations

import uuid
from datetime import datetime

from openrange.api.db.base import Base, new_uuid
from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.orm import Mapped, mapped_column


class VpnDevice(Base):
    __tablename__ = "vpn_devices"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(32))
    # Canonical base64 of the client's 32-byte WireGuard public key.
    public_key: Mapped[str] = mapped_column(Text, unique=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class VpnLease(Base):
    """One VPN pool address, held for exactly one device.

    Deleting the lease (revocation) returns the address to the pool.
    """

    __tablename__ = "vpn_leases"

    device_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("vpn_devices.id", ondelete="CASCADE"), primary_key=True
    )
    address: Mapped[str] = mapped_column(INET, unique=True)
    allocated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
