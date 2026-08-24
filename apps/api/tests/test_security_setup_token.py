"""Security gate: setup wizard token handling (plan Phase 14).

The one-time setup token gates creation of the first admin account.
Comparison must reject wrong tokens uniformly, including tokens of
different length (constant-time comparison must not crash on those).
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration

STRONG = "correct-horse-battery"


async def _begin_setup(client: AsyncClient) -> str:
    begin = await client.post("/api/setup/begin")
    assert begin.status_code == 200
    token: str = begin.json()["setup_url"].split("token=")[1]
    return token


async def test_complete_with_wrong_token_rejected(client: AsyncClient) -> None:
    await _begin_setup(client)
    res = await client.post(
        "/api/setup/complete",
        json={"username": "rootadmin", "password": STRONG, "token": "wrong-token-value"},
    )
    assert res.status_code == 403
    # The failed attempt must not consume or close setup mode...
    status = await client.get("/api/setup/status")
    assert status.json()["required"] is True


async def test_complete_with_wrong_length_token_rejected(client: AsyncClient) -> None:
    """compare_digest raises on unequal-length inputs; the route must
    translate any mismatch into the same uniform 403."""
    await _begin_setup(client)
    for bogus in ["", "a", "x" * 100]:
        res = await client.post(
            "/api/setup/complete",
            json={"username": "rootadmin", "password": STRONG, "token": bogus},
        )
        assert res.status_code == 403, (bogus, res.text)


async def test_complete_without_token_issued_rejected(client: AsyncClient) -> None:
    res = await client.post(
        "/api/setup/complete",
        json={"username": "rootadmin", "password": STRONG, "token": "never-issued"},
    )
    assert res.status_code == 403


async def test_valid_token_still_creates_admin(client: AsyncClient) -> None:
    token = await _begin_setup(client)
    res = await client.post(
        "/api/setup/complete",
        json={"username": "rootadmin", "password": STRONG, "token": token},
    )
    assert res.status_code == 200, res.text
    assert (await client.get("/api/setup/status")).json()["required"] is False
