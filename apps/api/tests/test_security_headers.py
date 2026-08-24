"""Security gate: response headers (plan Phase 14.2).

Every response from the API must carry the baseline hardening headers,
including error responses produced outside the middleware stack.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration

EXPECTED_HEADERS = {
    "x-content-type-options": "nosniff",
    "x-frame-options": "DENY",
    "referrer-policy": "strict-origin-when-cross-origin",
}


async def test_security_headers_on_success(client: AsyncClient) -> None:
    res = await client.get("/api/healthz")
    assert res.status_code == 200
    for name, value in EXPECTED_HEADERS.items():
        assert res.headers.get(name) == value, f"missing {name} on 200"
    csp = res.headers.get("content-security-policy", "")
    assert "default-src 'none'" in csp
    assert "frame-ancestors 'none'" in csp


async def test_security_headers_on_error_responses(client: AsyncClient) -> None:
    not_found = await client.get("/api/does-not-exist")
    assert not_found.status_code == 404
    for name, value in EXPECTED_HEADERS.items():
        assert not_found.headers.get(name) == value, f"missing {name} on 404"

    unauthenticated = await client.get("/api/users/me")
    assert unauthenticated.status_code == 401
    for name, value in EXPECTED_HEADERS.items():
        assert unauthenticated.headers.get(name) == value, f"missing {name} on 401"


async def test_x_frame_options_is_deny_not_allowlist(client: AsyncClient) -> None:
    res = await client.get("/api/healthz")
    assert res.headers.get("x-frame-options") == "DENY"
