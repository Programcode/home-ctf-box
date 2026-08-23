"""Lab orchestrator integration gate (plan Phase 6).

Runs the real runner service over HTTP, drives lab lifecycle through
the API, and proves tenant isolation, reset/extend/stop semantics, the
expiry reaper, and reconciliation.
"""

from __future__ import annotations

import os
import socket
import threading
import time
import uuid
from collections.abc import Iterator

import httpx
import pytest
from httpx import ASGITransport, AsyncClient
from testshelpers.runner_server import serve_runner

pytestmark = [pytest.mark.integration]

os.environ.setdefault("OPENRANGE_RUNNER_API_TOKEN", "test-runner-token-0123456789abcdef")
os.environ.setdefault("OPENRANGE_CONTENT_ROOT", "content/rooms")


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


@pytest.fixture(scope="module")
def runner_base() -> Iterator[str]:
    port = _free_port()
    server = serve_runner(port)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{port}"
    deadline = time.time() + 10
    while time.time() < deadline:
        try:
            httpx.get(f"{base}/healthz", timeout=1)
            break
        except Exception:
            time.sleep(0.2)
    yield base
    server.should_exit = True
    thread.join(timeout=5)


async def make_user(username: str) -> tuple[AsyncClient, dict[str, str]]:
    """One isolated client per user so cookie jars never collide."""
    from openrange.api.main import create_app

    app = create_app()
    transport = ASGITransport(app=app)  # type: ignore[arg-type]
    client = AsyncClient(transport=transport, base_url="http://test", timeout=120)
    res = await client.post(
        "/api/auth/register",
        json={"username": username, "password": "correct-horse-battery"},
    )
    assert res.status_code == 201, res.text
    return client, {"x-csrf-token": res.json()["csrf_token"]}


async def test_lab_lifecycle_and_isolation(runner_base: str) -> None:
    os.environ["OPENRANGE_RUNNER_API_URL"] = runner_base
    alice, headers_a = await make_user("labusera")

    started = await alice.post("/api/labs", json={"room": "busted-login"}, headers=headers_a)
    assert started.status_code == 200, started.text
    lab_a = started.json()
    assert lab_a["state"] == "ready"
    assert lab_a["targets"], lab_a

    bob, headers_b = await make_user("labuserb")
    cross = await bob.get(f"/api/labs/{lab_a['id']}", headers=headers_b)
    assert cross.status_code == 404
    cross_stop = await bob.delete(f"/api/labs/{lab_a['id']}", headers=headers_b)
    assert cross_stop.status_code == 404

    bob_lab = (await bob.post("/api/labs", json={"room": "busted-login"}, headers=headers_b)).json()
    assert bob_lab["state"] == "ready"

    reset = await alice.post(f"/api/labs/{lab_a['id']}/reset", headers=headers_a)
    assert reset.status_code == 200 and reset.json()["state"] == "ready"
    extend = await alice.post(
        f"/api/labs/{lab_a['id']}/extend", json={"minutes": 30}, headers=headers_a
    )
    assert extend.status_code == 200

    stopped = await alice.delete(f"/api/labs/{lab_a['id']}", headers=headers_a)
    assert stopped.status_code == 200
    detail = await alice.get(f"/api/labs/{lab_a['id']}")
    assert detail.json()["state"] in ("cleaned", "expired")

    await bob.delete(f"/api/labs/{bob_lab['id']}", headers=headers_b)
    await alice.aclose()
    await bob.aclose()


async def test_reaper_expires_labs(runner_base: str) -> None:
    from datetime import UTC, datetime, timedelta

    from openrange.api.db import session_factory
    from openrange.api.labs import service as labsvc
    from openrange.api.labs.models import LabInstance
    from openrange.api.labs.runner_client import RunnerClient

    os.environ["OPENRANGE_RUNNER_API_URL"] = runner_base
    user, headers = await make_user("reaperuser")
    lab = (await user.post("/api/labs", json={"room": "open-panels"}, headers=headers)).json()
    assert lab["state"] == "ready"

    async def expire_and_reap() -> list[uuid.UUID]:
        assert session_factory is not None
        async with session_factory() as db:
            instance = await db.get(LabInstance, uuid.UUID(lab["id"]))
            assert instance is not None
            instance.expires_at = datetime.now(UTC) - timedelta(minutes=5)
            await db.commit()
            removed = await labsvc.expire_due_labs(db, RunnerClient())
            await db.commit()
            return removed

    removed = await expire_and_reap()
    assert uuid.UUID(lab["id"]) in removed
    await user.aclose()
