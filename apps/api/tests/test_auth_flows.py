"""Auth/RBAC integration gate (plan Phase 2).

Covers: registration rules, login lockout, CSRF enforcement,
reset-token reuse, revoked sessions, MFA, and privilege-escalation
attempts.
"""

from __future__ import annotations

import pyotp
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration

STRONG = "correct-horse-battery"


async def _register(client: AsyncClient, username: str = "alice") -> dict[str, str]:
    res = await client.post(
        "/api/auth/register",
        json={"username": username, "password": STRONG},
    )
    assert res.status_code == 201, res.text
    data: dict[str, str] = res.json()
    return data


async def test_register_login_me_roundtrip(client: AsyncClient) -> None:
    data = await _register(client)
    me_res = await client.get("/api/users/me")
    assert me_res.status_code == 200
    assert me_res.json()["username"] == "alice"
    assert "progress:own" in me_res.json()["permissions"]

    await client.post("/api/auth/logout", headers={"x-csrf-token": data["csrf_token"]})
    anon = await client.get("/api/users/me")
    assert anon.status_code == 401


async def test_weak_passwords_rejected(client: AsyncClient) -> None:
    for weak in ["short", "password", "12345678", f"contains-bob-{STRONG}"]:
        res = await client.post("/api/auth/register", json={"username": "bob", "password": weak})
        assert res.status_code == 400, (weak, res.text)


async def test_reserved_username_rejected(client: AsyncClient) -> None:
    res = await client.post("/api/auth/register", json={"username": "admin", "password": STRONG})
    assert res.status_code == 400


async def test_duplicate_username_rejected(client: AsyncClient) -> None:
    await _register(client, "carol")
    res = await client.post("/api/auth/register", json={"username": "carol", "password": STRONG})
    assert res.status_code == 400


async def test_login_lockout_after_repeated_failures(client: AsyncClient) -> None:
    await _register(client, "dave")
    for _ in range(10):
        bad = await client.post(
            "/api/auth/login", json={"username": "dave", "password": "wrong-password-x"}
        )
        assert bad.status_code == 401
    throttled = await client.post("/api/auth/login", json={"username": "dave", "password": STRONG})
    assert throttled.status_code == 429


async def test_csrf_required_for_cookie_mutations(client: AsyncClient) -> None:
    await _register(client, "erin")
    no_csrf = await client.patch("/api/users/me", json={"display_name": "E"})
    assert no_csrf.status_code == 403


async def test_reset_token_single_use_and_revokes_sessions(client: AsyncClient) -> None:
    from openrange.api.auth import service
    from openrange.api.auth.service import SessionContext
    from openrange.api.config import get_settings
    from openrange.api.db import session_factory

    await _register(client, "frank")
    assert session_factory is not None
    async with session_factory() as db:
        created = await service.request_password_reset(
            db, get_settings(), username="frank", ctx=SessionContext()
        )
        assert created is not None
        ok = await service.complete_password_reset(
            db, token=created, new_password="new-passphrase-99"
        )
        assert ok is True
        reused = await service.complete_password_reset(
            db, token=created, new_password="another-pass-77"
        )
        assert reused is False
        user = await service.get_user_by_username(db, "frank")
        assert user is not None
        live = [s for s in await service.list_sessions_for_user(db, user.id) if s.is_live]
        assert live == []


async def test_mfa_totp_flow(client: AsyncClient) -> None:
    data = await _register(client, "grace")
    csrf = {"x-csrf-token": data["csrf_token"]}
    enroll = await client.post("/api/users/me/mfa/totp", headers=csrf)
    assert enroll.status_code == 200
    secret = enroll.json()["secret"]

    confirm = await client.post(
        "/api/users/me/mfa/totp/confirm",
        json={"code": pyotp.TOTP(secret).now()},
        headers=csrf,
    )
    assert confirm.status_code == 200
    codes: list[str] = confirm.json()["recovery_codes"]
    assert len(codes) == 8

    await client.post("/api/auth/logout")

    login = await client.post("/api/auth/login", json={"username": "grace", "password": STRONG})
    assert login.json()["mfa_pending"] is True
    blocked = await client.get("/api/users/me")
    assert blocked.status_code == 403

    verify = await client.post(
        "/api/auth/mfa/verify",
        json={"code": pyotp.TOTP(secret).now()},
        headers={"x-csrf-token": login.json()["csrf_token"]},
    )
    assert verify.status_code == 200
    ok = await client.get("/api/users/me")
    assert ok.status_code == 200

    await client.post("/api/auth/logout", headers={"x-csrf-token": login.json()["csrf_token"]})
    second = await client.post("/api/auth/login", json={"username": "grace", "password": STRONG})
    recovery = await client.post(
        "/api/auth/mfa/verify",
        json={"code": codes[0]},
        headers={"x-csrf-token": second.json()["csrf_token"]},
    )
    assert recovery.status_code == 200


async def test_privilege_escalation_blocked(client: AsyncClient) -> None:
    await _register(client, "henry")
    res = await client.post("/api/setup/begin")
    assert res.status_code == 409


async def test_setup_wizard_creates_first_admin(client: AsyncClient) -> None:
    status = await client.get("/api/setup/status")
    assert status.json()["required"] is True

    begin = await client.post("/api/setup/begin")
    assert begin.status_code == 200
    token = begin.json()["setup_url"].split("token=")[1]

    complete = await client.post(
        "/api/setup/complete",
        json={"username": "rootadmin", "password": STRONG, "token": token},
    )
    assert complete.status_code == 200

    again = await client.post("/api/setup/begin")
    assert again.status_code == 409
    assert (await client.get("/api/setup/status")).json()["required"] is False
