"""Health endpoint: component states for the runner and the shared secret."""

from __future__ import annotations

from typing import Any

import httpx
import pytest
from openrange.gateway.main import create_app

SECRET = "test-gateway-secret"


@pytest.mark.usefixtures("gateway_app")
async def test_healthz_ok(client: httpx.AsyncClient) -> None:
    response = await client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "runner": True, "secret": True}


async def test_healthz_degraded_when_runner_down(build_gateway: Any, fake_runner: Any) -> None:
    fake_runner.fail = True
    app = build_gateway()
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://gateway.test") as http:
            response = await http.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "degraded", "runner": False, "secret": True}


async def test_healthz_degraded_without_secret(build_gateway: Any, fake_runner: Any) -> None:
    app = build_gateway(gateway_secret="")
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://gateway.test") as http:
            response = await http.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "degraded", "runner": True, "secret": False}


def test_entry_point_factory_builds_without_connections(fake_runner: Any) -> None:
    app = create_app(runner=fake_runner)
    assert app.title == "OpenRange Lab Gateway"
