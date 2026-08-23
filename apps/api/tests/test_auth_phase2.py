"""Phase 2 additions: rate limiting, session hygiene, export/deletion."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import select

pytestmark = pytest.mark.integration

STRONG = "correct-horse-battery"


async def _register(client: AsyncClient, username: str) -> dict[str, str]:
    res = await client.post("/api/auth/register", json={"username": username, "password": STRONG})
    assert res.status_code == 201, res.text
    return res.json()


async def test_login_issues_fresh_session_token(client: AsyncClient) -> None:
    """Session fixation: the pre-auth cookie (none here) must never be
    reused post-login; each login mints a distinct session token."""
    await _register(client, "fixa")
    first = await client.post("/api/auth/login", json={"username": "fixa", "password": STRONG})
    second = await client.post("/api/auth/login", json={"username": "fixa", "password": STRONG})
    cookie1 = first.cookies.get("openrange_session")
    cookie2 = second.cookies.get("openrange_session")
    assert cookie1 and cookie2 and cookie1 != cookie2


async def test_rate_limit_on_login(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    await _register(client, "ratelimit")
    monkeypatch.setenv("OPENRANGE_REDIS_URL", "redis://localhost:16379/0")
    from openrange.api.auth import ratelimit

    ratelimit._client = None  # force reconnect to the configured URL
    # The middleware allows 20 login attempts per 5 minutes per IP.
    statuses = []
    for _ in range(21):
        res = await client.post(
            "/api/auth/login", json={"username": "ratelimit", "password": "nope-nope-nope"}
        )
        statuses.append(res.status_code)
    assert 429 in statuses, statuses
    assert statuses[-1] == 429


async def test_email_verification_flow(client: AsyncClient) -> None:
    data = await _register(client, "maily")
    csrf = {"x-csrf-token": data["csrf_token"]}
    req = await client.post(
        "/api/users/me/email/verify-request",
        json={"email": "maily@example.com"},
        headers=csrf,
    )
    assert req.status_code == 200

    from openrange.api.auth.tokens import generate_token, hash_token
    from openrange.api.db import session_factory
    from openrange.api.users.models import EmailVerification

    assert session_factory is not None
    async with session_factory() as db:
        row = (await db.execute(select(EmailVerification))).scalar_one()
        # forge a raw token matching the stored hash to prove the round trip
        raw = generate_token(32)
        row.token_hash = hash_token(raw)
        await db.commit()

    confirm = await client.post("/api/auth/email/confirm", json={"code": raw})
    assert confirm.status_code == 200
    me = await client.get("/api/users/me")
    assert me.json()["email_verified"] is True


async def test_export_then_delete_account(client: AsyncClient) -> None:
    data = await _register(client, "gone")
    csrf = {"x-csrf-token": data["csrf_token"]}
    export = await client.get("/api/users/me/export")
    body = export.json()
    assert body["user"]["username"] == "gone"

    deleted = await client.post("/api/users/me/delete", headers=csrf)
    assert deleted.status_code == 200
    anon = await client.get("/api/users/me")
    assert anon.status_code == 401

    from openrange.api.db import session_factory
    from openrange.api.users.models import User

    assert session_factory is not None
    async with session_factory() as db:
        row = (await db.execute(select(User))).scalars().first()
        assert row is not None and row.deleted_at is not None
        assert row.password_hash is None
        assert row.email is None


async def test_oidc_disabled_returns_404(client: AsyncClient) -> None:
    res = await client.get("/api/auth/oidc/login", follow_redirects=False)
    assert res.status_code == 404


async def test_webauthn_begin_requires_auth(client: AsyncClient) -> None:
    res = await client.post("/api/auth/webauthn/register/begin")
    assert res.status_code == 401
