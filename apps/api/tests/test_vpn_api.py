"""VPN device management integration gate (plan Phase 7 remainder).

Real Postgres: device registration with server-side address allocation,
scoped-route config rendering, revocation semantics, gateway heartbeat,
pool exhaustion, and RBAC negatives.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select

pytestmark = pytest.mark.integration

STRONG = "correct-horse-battery"
GATEWAY_SECRET = "test-gateway-secret"
SERVER_PUB = base64.b64encode(b"S" * 32).decode()

_clients: list[AsyncClient] = []

_key_counter = 0


def make_key() -> str:
    global _key_counter
    _key_counter += 1
    return base64.b64encode(bytes([_key_counter % 255]) * 32).decode()


def vpn_settings(**overrides: Any) -> Any:
    from openrange.api.vpn.settings import VpnSettings

    values: dict[str, Any] = {
        "vpn_server_public_key": SERVER_PUB,
        "vpn_endpoint": "vpn.example.com:51820",
        "vpn_allowed_subnets": "172.30.0.0/16, 172.31.0.0/16",
        "gateway_secret": GATEWAY_SECRET,
    }
    values.update(overrides)
    return VpnSettings(**values)


def make_app(**settings_overrides: Any) -> FastAPI:
    from openrange.api.main import create_app
    from openrange.api.vpn.settings import get_vpn_settings

    app = create_app()
    resolved = vpn_settings(**settings_overrides)
    app.dependency_overrides[get_vpn_settings] = lambda: resolved
    return app


@pytest.fixture(autouse=True)
async def _close_clients() -> AsyncIterator[None]:
    yield
    while _clients:
        await _clients.pop().aclose()


async def _make_user(username: str) -> tuple[AsyncClient, dict[str, str], uuid.UUID]:
    """Isolated client per user so cookie jars never collide."""
    app = make_app()
    client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test", timeout=120)
    _clients.append(client)
    res = await client.post("/api/auth/register", json={"username": username, "password": STRONG})
    assert res.status_code == 201, res.text
    headers = {"x-csrf-token": res.json()["csrf_token"]}
    me = await client.get("/api/users/me")
    assert me.status_code == 200
    return client, headers, uuid.UUID(me.json()["id"])


async def _make_admin(username: str) -> tuple[AsyncClient, dict[str, str]]:
    from openrange.api.auth.service import grant_role
    from openrange.api.users.models import User

    client, headers, user_id = await _make_user(username)
    async with _db() as db:
        user = (await db.execute(select(User).where(User.id == user_id))).scalar_one()
        await grant_role(db, user, "admin")
        await db.commit()
    return client, headers


@asynccontextmanager
async def _db() -> AsyncIterator[Any]:
    # Import lazily: the factory is created when the app first serves a
    # request, so the module-level symbol is still None at import time.
    from openrange.api.db import session_factory as sf

    assert sf is not None
    async with sf() as session:
        yield session


def _signed_headers(
    body: bytes, secret: str = GATEWAY_SECRET, *, timestamp: int | None = None
) -> dict[str, str]:
    ts = str(int(time.time() if timestamp is None else timestamp))
    digest = hmac.new(secret.encode(), ts.encode() + b":" + body, hashlib.sha256).hexdigest()
    return {"X-Gateway-Timestamp": ts, "X-Gateway-Signature": digest}


async def _create_device(
    client: AsyncClient,
    headers: dict[str, str],
    *,
    name: str = "laptop",
    public_key: str | None = None,
) -> dict[str, Any]:
    res = await client.post(
        "/api/vpn/devices",
        json={"name": name, "public_key": public_key or make_key()},
        headers=headers,
    )
    assert res.status_code == 200, res.text
    return res.json()


async def test_device_lifecycle_and_scoped_config() -> None:
    alice, headers_a, _uid = await _make_user("vpnalice")

    created = await _create_device(alice, headers_a)
    device = created["device"]
    config = created["config"]
    assert device["address"] == "10.99.0.1"
    assert device["revoked_at"] is None

    # The rendered config carries ONLY the scoped lab subnets.
    assert config.startswith("[Interface]")
    assert "Address = 10.99.0.1/32" in config
    assert "[Peer]" in config
    assert f"PublicKey = {SERVER_PUB}" in config
    assert "AllowedIPs = 172.30.0.0/16, 172.31.0.0/16" in config
    assert "Endpoint = vpn.example.com:51820" in config
    assert "PersistentKeepalive = 25" in config
    assert "0.0.0.0/0" not in config
    assert "::/0" not in config
    assert "PrivateKey =" not in config

    listed = await alice.get("/api/vpn/devices")
    assert listed.status_code == 200
    entries = listed.json()
    assert len(entries) == 1
    assert entries[0]["address"] == "10.99.0.1"

    status = await alice.get(f"/api/vpn/devices/{device['id']}/status")
    assert status.status_code == 200
    assert status.json()["last_seen_at"] is None

    # Second device gets the next pool address.
    second = await _create_device(alice, headers_a, name="phone")
    assert second["device"]["address"] == "10.99.0.2"


async def test_public_key_and_name_validation() -> None:
    alice, headers_a, _uid = await _make_user("vpnvalid")

    bad_keys = [
        "not-a-real-key",
        base64.b64encode(b"short").decode(),  # decodes to 5 bytes
        "A" * 43,  # missing padding
        base64.urlsafe_b64encode(b"url-safe-alphabet!!!!!!").decode(),  # - and _
    ]
    for key in bad_keys:
        res = await alice.post(
            "/api/vpn/devices", json={"name": "laptop", "public_key": key}, headers=headers_a
        )
        assert res.status_code == 422, f"{key}: {res.text}"

    bad_names = ["bad name!", "x" * 33, "", "-é-"]
    for name in bad_names:
        res = await alice.post(
            "/api/vpn/devices",
            json={"name": name, "public_key": make_key()},
            headers=headers_a,
        )
        assert res.status_code == 422, f"{name!r}: {res.text}"


async def test_duplicate_public_key_conflicts() -> None:
    alice, headers_a, _uid = await _make_user("vpndup")
    bob, headers_b, _bid = await _make_user("vpndup2")
    shared = make_key()
    await _create_device(alice, headers_a, public_key=shared)
    res = await bob.post(
        "/api/vpn/devices", json={"name": "laptop", "public_key": shared}, headers=headers_b
    )
    assert res.status_code == 409
    assert "already registered" in res.json()["detail"]


async def test_address_pool_exhaustion_returns_409() -> None:
    app = make_app(vpn_pool="10.99.0.0/30")
    client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test", timeout=120)
    _clients.append(client)
    res = await client.post(
        "/api/auth/register", json={"username": "vpnpoolex", "password": STRONG}
    )
    assert res.status_code == 201, res.text
    headers = {"x-csrf-token": res.json()["csrf_token"]}

    # /30 leaves three host addresses; the fourth registration must fail.
    for i in range(3):
        made = await _create_device(client, headers, name=f"d{i}")
        assert made["device"]["address"].startswith("10.99.0.")
    exhausted = await client.post(
        "/api/vpn/devices",
        json={"name": "d3", "public_key": make_key()},
        headers=headers,
    )
    assert exhausted.status_code == 409
    assert "exhausted" in exhausted.json()["detail"]

    # Revoking one device frees its address immediately.
    victim_id = (await client.get("/api/vpn/devices")).json()[0]["id"]
    freed = await client.delete(f"/api/vpn/devices/{victim_id}", headers=headers)
    assert freed.status_code == 200
    retry = await client.post(
        "/api/vpn/devices",
        json={"name": "d3", "public_key": make_key()},
        headers=headers,
    )
    assert retry.status_code == 200, retry.text


async def test_revocation_invalidates_config_and_frees_address() -> None:
    alice, headers_a, _uid = await _make_user("vpnrevoke")

    created = await _create_device(alice, headers_a, public_key=make_key())
    device_id = created["device"]["id"]
    pubkey = created["device"]["public_key"]
    assert created["device"]["address"] == "10.99.0.1"

    revoked = await alice.delete(f"/api/vpn/devices/{device_id}", headers=headers_a)
    assert revoked.status_code == 200 and revoked.json()["revoked"] is True

    gone_config = await alice.get(f"/api/vpn/devices/{device_id}/config.qr")
    assert gone_config.status_code == 410

    status = await alice.get(f"/api/vpn/devices/{device_id}/status")
    assert status.status_code == 200
    assert status.json()["revoked_at"] is not None

    # A revoked device must not be heartbeaten back to life.
    body = f'{{"device_public_key": "{pubkey}"}}'.encode()
    beat = await alice.post("/internal/vpn/heartbeat", content=body, headers=_signed_headers(body))
    assert beat.status_code == 404

    # The lease was removed: a fresh device reuses the freed address.
    fresh = await _create_device(alice, headers_a, name="after-revoke")
    assert fresh["device"]["address"] == "10.99.0.1"


async def test_gateway_heartbeat_updates_last_seen() -> None:
    alice, headers_a, _uid = await _make_user("vpnbeat")
    created = await _create_device(alice, headers_a)
    pubkey = created["device"]["public_key"]
    device_id = created["device"]["id"]

    body = f'{{"device_public_key": "{pubkey}"}}'.encode()
    ok = await alice.post("/internal/vpn/heartbeat", content=body, headers=_signed_headers(body))
    assert ok.status_code == 200 and ok.json() == {"ok": True}

    status = await alice.get(f"/api/vpn/devices/{device_id}/status")
    assert status.status_code == 200
    assert status.json()["last_seen_at"] is not None

    unknown_body = b'{"device_public_key": "' + make_key().encode() + b'"}'
    unknown = await alice.post(
        "/internal/vpn/heartbeat", content=unknown_body, headers=_signed_headers(unknown_body)
    )
    assert unknown.status_code == 404

    bad_sig = await alice.post(
        "/internal/vpn/heartbeat", content=body, headers=_signed_headers(body, secret="wrong")
    )
    assert bad_sig.status_code == 401

    stale = await alice.post(
        "/internal/vpn/heartbeat",
        content=body,
        headers=_signed_headers(body, timestamp=int(time.time()) - 400),
    )
    assert stale.status_code == 401

    missing = await alice.post("/internal/vpn/heartbeat", content=body)
    assert missing.status_code == 401

    junk = b"{not json"
    malformed = await alice.post(
        "/internal/vpn/heartbeat", content=junk, headers=_signed_headers(junk)
    )
    assert malformed.status_code == 400

    empty = b'{"nope": true}'
    no_field = await alice.post(
        "/internal/vpn/heartbeat", content=empty, headers=_signed_headers(empty)
    )
    assert no_field.status_code == 400


async def test_config_format_guard_and_content_type() -> None:
    alice, headers_a, _uid = await _make_user("vpnformat")
    created = await _create_device(alice, headers_a)
    device_id = created["device"]["id"]

    svg = await alice.get(f"/api/vpn/devices/{device_id}/config.qr?format=svg")
    assert svg.status_code == 400
    assert "client-side" in svg.json()["detail"]

    text = await alice.get(f"/api/vpn/devices/{device_id}/config.qr")
    assert text.status_code == 200
    assert text.headers["content-type"].startswith("text/plain")
    assert text.text.startswith("[Interface]")


async def test_rbac_negatives_and_admin_listing() -> None:
    alice, headers_a, alice_id = await _make_user("vpnrbaca")
    bob, headers_b, _bob_id = await _make_user("vpnrbacb")
    admin, admin_h = await _make_admin("vpnrbacadmin")

    unauthed = AsyncClient(transport=ASGITransport(app=make_app()), base_url="http://test")
    _clients.append(unauthed)
    anon = await unauthed.post(
        "/api/vpn/devices", json={"name": "laptop", "public_key": make_key()}
    )
    assert anon.status_code == 401

    created = await _create_device(alice, headers_a)
    device_id = created["device"]["id"]

    # Another learner cannot see, configure, or revoke Alice's device.
    for path in (
        f"/api/vpn/devices/{device_id}/config.qr",
        f"/api/vpn/devices/{device_id}/status",
    ):
        cross = await bob.get(path, headers=headers_b)
        assert cross.status_code == 404, path
    cross_delete = await bob.delete(f"/api/vpn/devices/{device_id}", headers=headers_b)
    assert cross_delete.status_code == 404

    forbidden_list = await bob.get("/api/vpn/admin/devices", headers=headers_b)
    assert forbidden_list.status_code == 403

    listing = await admin.get("/api/vpn/admin/devices", headers=admin_h)
    assert listing.status_code == 200
    entries = listing.json()
    assert len(entries) == 1
    assert entries[0]["user_id"] == str(alice_id)

    # A user with no roles at all loses vpn:issue.
    from openrange.api.users.models import UserRole

    async with _db() as db:
        await db.execute(delete(UserRole).where(UserRole.user_id == alice_id))
        await db.commit()
    stripped = await alice.post(
        "/api/vpn/devices",
        json={"name": "laptop", "public_key": make_key()},
        headers=headers_a,
    )
    assert stripped.status_code == 403
    assert "vpn:issue" in stripped.json()["detail"]


async def test_unknown_device_ids_are_hidden() -> None:
    alice, headers_a, _uid = await _make_user("vpnunknown")
    random_id = str(uuid.uuid4())
    for method, path in (
        ("GET", f"/api/vpn/devices/{random_id}/config.qr"),
        ("GET", f"/api/vpn/devices/{random_id}/status"),
        ("DELETE", f"/api/vpn/devices/{random_id}"),
    ):
        res = await alice.request(method, path, headers=headers_a)
        assert res.status_code == 404, path
    garbage = await alice.get("/api/vpn/devices/not-a-uuid/config.qr", headers=headers_a)
    assert garbage.status_code == 404
