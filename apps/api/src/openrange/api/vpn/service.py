"""VPN device lifecycle: key validation, address allocation, config rendering.

Scope rules (docs/contracts/vpn-api.md):
- the server never sees a private key; clients generate their own keypair
  and register only the public key;
- rendered configs allow ONLY the lab subnets from settings, never
  0.0.0.0/0;
- revocation frees the lease and permanently retires the config.
"""

from __future__ import annotations

import hashlib
import hmac
import ipaddress
import time
from datetime import UTC, datetime
from typing import Any

from openrange.api.db.base import new_uuid
from openrange.api.vpn.models import VpnDevice, VpnLease
from openrange.api.vpn.settings import VpnSettings
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

_ALLOCATION_ATTEMPTS = 3


class VpnProblem(Exception):
    """Domain error translated to an RFC 9457 problem response."""

    def __init__(self, status: int, title: str, detail: str) -> None:
        super().__init__(detail)
        self.status = status
        self.title = title
        self.detail = detail


def _require_issue_config(settings: VpnSettings) -> tuple[str, list[str], str]:
    if not settings.vpn_server_public_key or not settings.vpn_endpoint:
        raise VpnProblem(
            503,
            "Service Unavailable",
            "vpn issuance is not configured on this installation",
        )
    subnets = settings.allowed_subnets()
    if not subnets:
        raise VpnProblem(503, "Service Unavailable", "no lab subnets are scoped for vpn")
    return settings.vpn_server_public_key, subnets, settings.vpn_endpoint


def render_client_config(*, address: str, settings: VpnSettings) -> str:
    """Render the wg-quick client config text for one device.

    The Interface section intentionally carries no PrivateKey line: the
    private key never leaves the client that generated the keypair.
    """
    server_public_key, subnets, endpoint = _require_issue_config(settings)
    return (
        "[Interface]\n"
        "# Paste your own private key here; it is never sent to the server.\n"
        f"Address = {address}/32\n"
        "\n"
        "[Peer]\n"
        f"PublicKey = {server_public_key}\n"
        f"AllowedIPs = {', '.join(subnets)}\n"
        f"Endpoint = {endpoint}\n"
        "PersistentKeepalive = 25\n"
    )


async def allocate_address(db: AsyncSession, settings: VpnSettings) -> str:
    """Return the lowest free host address in the VPN pool."""
    network = settings.pool_network()
    rows = (await db.execute(select(VpnLease.address))).scalars().all()
    taken = {int(ipaddress.ip_address(a)) for a in rows}
    for offset in range(1, network.num_addresses):
        candidate = int(network.network_address) + offset
        if candidate not in taken:
            return str(network.network_address + offset)
    raise VpnProblem(409, "Conflict", "vpn address pool exhausted")


async def register_device(
    db: AsyncSession, *, user_id: Any, name: str, public_key: str, settings: VpnSettings
) -> tuple[VpnDevice, VpnLease, str]:
    """Create device + lease and return them with the rendered client config."""
    # Fail before touching the pool when issuance is unconfigured. The
    # placeholder address is never bound anywhere; it only exercises the
    # template renderer.
    render_client_config(address="127.0.0.1", settings=settings)  # noqa: S104 - placeholder, never bound

    duplicate = await db.scalar(select(VpnDevice).where(VpnDevice.public_key == public_key))
    if duplicate is not None:
        raise VpnProblem(409, "Conflict", "public key already registered")

    for _attempt in range(_ALLOCATION_ATTEMPTS):
        address = await allocate_address(db, settings)
        device = VpnDevice(id=new_uuid(), user_id=user_id, name=name, public_key=public_key)
        lease = VpnLease(device_id=device.id, address=address)
        db.add_all([device, lease])
        try:
            async with db.begin_nested():
                await db.flush()
        except IntegrityError:
            # Concurrent registration claimed the address or key first.
            continue
        return device, lease, render_client_config(address=address, settings=settings)
    raise VpnProblem(409, "Conflict", "could not allocate a free vpn address")


async def revoke_device(db: AsyncSession, device: VpnDevice) -> None:
    """Revoke the device and return its address to the pool."""
    if device.revoked_at is None:
        device.revoked_at = datetime.now(UTC)
    lease = await db.get(VpnLease, device.id)
    if lease is not None:
        await db.delete(lease)


async def record_heartbeat(db: AsyncSession, *, device_public_key: str) -> None:
    device = await db.scalar(
        select(VpnDevice).where(
            VpnDevice.public_key == device_public_key,
            VpnDevice.revoked_at.is_(None),
        )
    )
    if device is None:
        # Unknown and revoked devices are indistinguishable here so a
        # retired peer cannot be probed back into existence.
        raise VpnProblem(404, "Not Found", "unknown device")
    device.last_seen_at = datetime.now(UTC)


def verify_gateway_signature(
    *,
    timestamp: str | None,
    signature: str | None,
    body: bytes,
    secret: str,
    replay_window_seconds: int = 300,
    now: float | None = None,
) -> None:
    """Gateway HMAC auth over ``f"{timestamp}:{body}"`` (runner-auth pattern).

    Uses OPENRANGE_GATEWAY_SECRET instead of the runner token; header
    names are X-Gateway-Timestamp / X-Gateway-Signature.
    """
    if not secret:
        raise VpnProblem(401, "Unauthorized", "gateway secret is not configured")
    if timestamp is None or signature is None:
        raise VpnProblem(401, "Unauthorized", "missing X-Gateway-Timestamp/X-Gateway-Signature")
    try:
        issued_at = int(timestamp)
    except ValueError as exc:
        raise VpnProblem(401, "Unauthorized", "timestamp must be unix seconds") from exc
    current = time.time() if now is None else now
    if abs(current - issued_at) > replay_window_seconds:
        raise VpnProblem(401, "Unauthorized", "timestamp outside the replay window")
    expected = hmac.new(
        secret.encode(), timestamp.encode() + b":" + body, hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(expected.encode(), signature.encode()):
        raise VpnProblem(401, "Unauthorized", "invalid signature")


def device_view(device: VpnDevice, *, address: str | None = None) -> dict[str, Any]:
    view: dict[str, Any] = {
        "id": str(device.id),
        "name": device.name,
        "public_key": device.public_key,
        "created_at": device.created_at.isoformat(),
        "revoked_at": device.revoked_at.isoformat() if device.revoked_at else None,
        "last_seen_at": device.last_seen_at.isoformat() if device.last_seen_at else None,
        "address": address,
    }
    return view
