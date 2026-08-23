"""HMAC authentication contract: signatures, replay window, healthz exemption."""

from __future__ import annotations

import time

import pytest

pytestmark = pytest.mark.integration


async def test_healthz_is_unauthenticated(runner_client) -> None:
    response = await runner_client.raw_get("/healthz")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["docker"] is True


async def test_missing_signature_is_unauthorized(runner_client) -> None:
    response = await runner_client.request(
        "POST", "/v1/reconcile", {"known_instance_ids": []}, omit_signature=True
    )
    assert response.status_code == 401
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["title"] == "Unauthorized"


async def test_bad_signature_is_unauthorized(runner_client) -> None:
    response = await runner_client.request(
        "POST",
        "/v1/reconcile",
        {"known_instance_ids": []},
        signature="0" * 64,
    )
    assert response.status_code == 401
    assert response.json()["title"] == "Unauthorized"


@pytest.mark.parametrize("offset", [-301, 301])
async def test_stale_timestamp_is_unauthorized(runner_client, offset: int) -> None:
    response = await runner_client.request(
        "POST",
        "/v1/reconcile",
        {"known_instance_ids": []},
        timestamp=int(time.time()) + offset,
    )
    assert response.status_code == 401
    assert "replay window" in response.json()["detail"]


async def test_non_numeric_timestamp_is_unauthorized(runner_client) -> None:
    response = await runner_client.request(
        "POST",
        "/v1/reconcile",
        {"known_instance_ids": []},
        timestamp="not-a-timestamp",
    )
    assert response.status_code == 401


async def test_signature_covers_body(runner_client) -> None:
    """A signature valid for one body must not authorize a different body."""
    signed = await runner_client.signed_for_body(
        "POST", "/v1/reconcile", b'{"known_instance_ids": []}'
    )
    assert signed.status_code == 200
    tampered = await runner_client.with_headers(
        "POST",
        "/v1/reconcile",
        body=b'{"known_instance_ids": ["tampered"]}',
        headers=dict(signed.request.headers),
    )
    assert tampered.status_code == 401
