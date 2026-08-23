"""Proxy auth matrix, streaming roundtrip, header injection, and redaction."""

from __future__ import annotations

import logging
import os
from collections.abc import AsyncIterator
from typing import Any
from urllib.parse import urlencode

import httpx
import pytest
from openrange.gateway.tokens import mint_token

LAB_ID = "lab-1a2b3c4d"
SECRET = "test-gateway-secret"


def _proxy_url(port: int, path: str = "/", **params: str) -> str:
    url = f"/proxy/{LAB_ID}/{port}{path}"
    if params:
        url = f"{url}?{urlencode(params)}"
    return url


def _token_for(echo_port: int, **overrides: Any) -> str:
    params: dict[str, Any] = {
        "secret": SECRET,
        "sub": "user-1",
        "lab": LAB_ID,
        "ports": [echo_port],
    }
    params.update(overrides)
    return str(mint_token(**params))


async def test_streaming_post_roundtrip(
    client: httpx.AsyncClient, echo_target: tuple[str, int]
) -> None:
    port = echo_target[1]
    chunks = [os.urandom(128 * 1024) for _ in range(8)]
    expected = b"".join(chunks)

    async def body() -> AsyncIterator[bytes]:
        for chunk in chunks:
            yield chunk

    response = await client.post(
        _proxy_url(port), content=body(), params={"token": _token_for(port)}
    )
    assert response.status_code == 200, response.text
    assert response.content == expected


async def test_get_roundtrip_and_query_forwarding(
    client: httpx.AsyncClient, echo_target: tuple[str, int]
) -> None:
    port = echo_target[1]
    token = _token_for(port)
    response = await client.get(_proxy_url(port, "/headers", token=token, keep="1"))
    assert response.status_code == 200
    payload = response.json()
    assert "token" not in payload["query_keys"]
    assert "keep" in payload["query_keys"]
    assert payload["x_forwarded_proto"] == "http"
    assert payload["x_forwarded_host"] == "gateway.test"
    assert payload["x_forwarded_port"] == "80"
    forwarded_for = (payload["x_forwarded_for"] or "").split(",")[-1].strip()
    assert forwarded_for == "127.0.0.1"


async def test_authorization_and_cookie_not_forwarded(
    client: httpx.AsyncClient, echo_target: tuple[str, int]
) -> None:
    port = echo_target[1]
    token = _token_for(port)
    response = await client.get(
        _proxy_url(port, "/headers"),
        headers={"Authorization": f"Bearer {token}", "Cookie": "session=platform-secret"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["authorization"] is None
    assert payload["cookie"] is None


async def test_missing_token_is_401(
    client: httpx.AsyncClient, echo_target: tuple[str, int]
) -> None:
    response = await client.get(_proxy_url(echo_target[1]))
    assert response.status_code == 401
    assert response.headers["content-type"].startswith("application/problem+json")


async def test_bad_signature_is_401(
    client: httpx.AsyncClient, echo_target: tuple[str, int]
) -> None:
    token = _token_for(echo_target[1])
    forged = token[:-6] + ("AAAAAA" if token[-6:] != "AAAAAA" else "BBBBBB")
    response = await client.get(_proxy_url(echo_target[1]), params={"token": forged})
    assert response.status_code == 401


async def test_expired_token_is_401(
    client: httpx.AsyncClient, echo_target: tuple[str, int]
) -> None:
    token = _token_for(echo_target[1], ttl_seconds=-5)
    response = await client.get(_proxy_url(echo_target[1]), params={"token": token})
    assert response.status_code == 401
    assert "expired" in response.text


async def test_wrong_lab_is_403(client: httpx.AsyncClient, echo_target: tuple[str, int]) -> None:
    token = _token_for(echo_target[1], lab="lab-other")
    response = await client.get(_proxy_url(echo_target[1]), params={"token": token})
    assert response.status_code == 403


async def test_disallowed_port_is_403(
    client: httpx.AsyncClient, echo_target: tuple[str, int]
) -> None:
    token = _token_for(echo_target[1])
    other_port = echo_target[1] + 1
    response = await client.get(f"/proxy/{LAB_ID}/{other_port}/", params={"token": token})
    assert response.status_code == 403


async def test_unknown_instance_is_404(
    client: httpx.AsyncClient, echo_target: tuple[str, int]
) -> None:
    token = _token_for(echo_target[1], lab="lab-unknown")
    response = await client.get(f"/proxy/lab-unknown/{echo_target[1]}/", params={"token": token})
    assert response.status_code == 404


async def test_runner_down_is_502(
    client: httpx.AsyncClient,
    fake_runner: Any,
    echo_target: tuple[str, int],
) -> None:
    fake_runner.fail = True
    token = _token_for(echo_target[1])
    response = await client.get(_proxy_url(echo_target[1]), params={"token": token})
    assert response.status_code == 502


async def test_malformed_instance_id_is_400(client: httpx.AsyncClient) -> None:
    response = await client.get("/proxy/bad..id/8000/", params={"token": "anything"})
    assert response.status_code == 400


@pytest.mark.usefixtures("gateway_app")
async def test_request_id_header_and_log_redaction(
    client: httpx.AsyncClient, echo_target: tuple[str, int], caplog: pytest.LogCaptureFixture
) -> None:
    token = _token_for(echo_target[1])
    with caplog.at_level(logging.INFO):
        response = await client.get(_proxy_url(echo_target[1], "/headers", token=token))
    request_id = response.headers["x-request-id"]
    assert request_id
    # Gateway log records must never contain the token or a query string.
    gateway_records = [r for r in caplog.records if r.name.startswith("openrange.gateway")]
    assert gateway_records, "expected gateway log records"
    for record in gateway_records:
        rendered = record.getMessage() + repr(
            {k: v for k, v in record.__dict__.items() if k != "message"}
        )
        assert token not in rendered
    proxy_records = [
        r for r in gateway_records if str(getattr(r, "path", "")).startswith("/proxy/")
    ]
    assert proxy_records, "expected the proxied request to be logged"
    entry = proxy_records[0]
    assert str(entry.request_id) == request_id
    assert "?" not in str(entry.path)
