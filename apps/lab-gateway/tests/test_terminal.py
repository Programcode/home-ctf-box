"""Terminal bridge tests against a live uvicorn instance and an asyncssh echo server."""

from __future__ import annotations

import asyncio
import contextlib
import json
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any
from urllib.parse import urlencode

import pytest
import uvicorn
from fastapi import FastAPI
from openrange.gateway.tokens import mint_token
from websockets.asyncio.client import ClientConnection
from websockets.asyncio.client import connect as ws_connect
from websockets.exceptions import ConnectionClosed

LAB_ID = "lab-1a2b3c4d"
SECRET = "test-gateway-secret"
SSH_USERNAME = "labuser"
SSH_PASSWORD = "labpass"

GatewayFactory = Callable[..., Awaitable[tuple[str, FastAPI]]]


@pytest.fixture
async def make_live_gateway(build_gateway: Callable[..., FastAPI]) -> AsyncIterator[GatewayFactory]:
    created: list[tuple[uvicorn.Server, asyncio.Task[None]]] = []

    async def factory(**overrides: Any) -> tuple[str, FastAPI]:
        app = build_gateway(**overrides)
        config = uvicorn.Config(
            app, host="127.0.0.1", port=0, log_level="warning", access_log=False
        )
        server = uvicorn.Server(config)
        serve_task = asyncio.create_task(server.serve(), name="uvicorn-gateway")
        for _ in range(300):
            if server.started:
                break
            await asyncio.sleep(0.02)
        else:
            raise RuntimeError("gateway did not start")
        assert server.servers
        port = server.servers[0].sockets[0].getsockname()[1]
        created.append((server, serve_task))
        return f"ws://127.0.0.1:{port}", app

    yield factory
    for server, serve_task in created:
        server.should_exit = True
        with contextlib.suppress(asyncio.TimeoutError):
            await asyncio.wait_for(serve_task, timeout=15)


def _terminal_url(base: str, token: str, resume: str | None = None) -> str:
    params: dict[str, str] = {"token": token}
    if resume is not None:
        params["resume"] = resume
    return f"{base}/terminal/{LAB_ID}?{urlencode(params)}"


def _ssh_token(ssh: bool = True, **overrides: Any) -> str:
    params: dict[str, Any] = {
        "secret": SECRET,
        "sub": "user-1",
        "lab": LAB_ID,
        "ports": [22],
        "ssh": ssh,
        "ssh_user": SSH_USERNAME,
        "ssh_pass": SSH_PASSWORD,
    }
    params.update(overrides)
    return str(mint_token(**params))


@contextlib.asynccontextmanager
async def _open_terminal(
    url: str,
) -> AsyncIterator[tuple[ClientConnection, str]]:
    async with ws_connect(url, open_timeout=5, close_timeout=2) as ws:
        hello = json.loads(await asyncio.wait_for(ws.recv(), timeout=5))
        assert hello["type"] == "session"
        yield ws, str(hello["session_id"])


async def _expect_close(ws: ClientConnection, code: int) -> None:
    with pytest.raises(ConnectionClosed) as excinfo:
        await asyncio.wait_for(ws.recv(), timeout=5)
    closed = excinfo.value.rcvd
    assert closed is not None
    assert closed.code == code


async def test_echo_roundtrip_and_resize(make_live_gateway: GatewayFactory) -> None:
    base, _app = await make_live_gateway()
    url = _terminal_url(base, _ssh_token())
    async with _open_terminal(url) as (ws, _):
        await ws.send(b"ping-one")
        assert await asyncio.wait_for(ws.recv(), timeout=5) == b"ping-one"
        await ws.send(json.dumps({"type": "resize", "cols": 120, "rows": 40}))
        await ws.send(b"ping-two")
        assert await asyncio.wait_for(ws.recv(), timeout=5) == b"ping-two"


async def test_resize_reaches_pty(
    make_live_gateway: GatewayFactory, ssh_target: tuple[int, list[tuple[int, int]]]
) -> None:
    _, resizes = ssh_target
    base, _app = await make_live_gateway()
    url = _terminal_url(base, _ssh_token())
    async with _open_terminal(url) as (ws, _):
        await ws.send(json.dumps({"type": "resize", "cols": 137, "rows": 41}))
        for _ in range(100):
            if (137, 41) in resizes:
                break
            await asyncio.sleep(0.05)
        assert (137, 41) in resizes


async def test_clean_close_control_frame(make_live_gateway: GatewayFactory) -> None:
    base, _ = await make_live_gateway()
    async with ws_connect(_terminal_url(base, _ssh_token()), open_timeout=5) as ws:
        json.loads(await ws.recv())
        await ws.send(json.dumps({"type": "close"}))
        await _expect_close(ws, 1000)


async def test_invalid_token_denied_1008(make_live_gateway: GatewayFactory) -> None:
    base, _ = await make_live_gateway()
    async with ws_connect(_terminal_url(base, "lab-v1.bogus.bogus"), open_timeout=5) as ws:
        await _expect_close(ws, 1008)


async def test_ssh_false_denied_1008(make_live_gateway: GatewayFactory) -> None:
    base, _ = await make_live_gateway()
    async with ws_connect(_terminal_url(base, _ssh_token(ssh=False)), open_timeout=5) as ws:
        await _expect_close(ws, 1008)


async def test_wrong_lab_denied_1008(make_live_gateway: GatewayFactory) -> None:
    base, _ = await make_live_gateway()
    async with ws_connect(
        f"{base}/terminal/lab-other?" + urlencode({"token": _ssh_token()}), open_timeout=5
    ) as ws:
        await _expect_close(ws, 1008)


async def test_concurrency_cap_returns_1013_and_evicts_grace(
    make_live_gateway: GatewayFactory,
) -> None:
    base, _ = await make_live_gateway(max_sessions_per_lab=1)
    token = _ssh_token()

    async with _open_terminal(_terminal_url(base, token)) as (_ws, first_sid):
        async with ws_connect(_terminal_url(base, token), open_timeout=5) as second:
            await _expect_close(second, 1013)

    # The closed session now sits in the reconnect-grace window, but a new
    # opener must win the slot by evicting it.
    async with _open_terminal(_terminal_url(base, token)) as (_third, third_sid):
        assert third_sid != first_sid
        with pytest.raises(ConnectionClosed) as excinfo:
            async with ws_connect(
                _terminal_url(base, token, resume=first_sid), open_timeout=5
            ) as stale:
                await asyncio.wait_for(stale.recv(), timeout=5)
        assert excinfo.value.rcvd is not None
        assert excinfo.value.rcvd.code == 1008


async def test_resume_within_grace_reuses_session(make_live_gateway: GatewayFactory) -> None:
    base, _ = await make_live_gateway(resume_ttl_seconds=30.0)
    token = _ssh_token()
    async with _open_terminal(_terminal_url(base, token)) as (ws, sid):
        await ws.send(b"before-drop")
        assert await asyncio.wait_for(ws.recv(), timeout=5) == b"before-drop"
        ws.transport.abort()  # simulate a hard network drop, not a clean close
        await asyncio.sleep(0.05)

    # Wait out the hard-drop teardown tick, then reattach to the same channel.
    await asyncio.sleep(0.3)
    async with _open_terminal(_terminal_url(base, token, resume=sid)) as (resumed, sid2):
        assert sid2 == sid
        await resumed.send(b"after-resume")
        assert await asyncio.wait_for(resumed.recv(), timeout=5) == b"after-resume"


async def test_output_buffered_during_disconnect_is_delivered_on_resume(
    make_live_gateway: GatewayFactory,
) -> None:
    base, _ = await make_live_gateway(resume_ttl_seconds=30.0)
    token = _ssh_token()
    async with _open_terminal(_terminal_url(base, token)) as (ws, sid):
        # PUSH makes the echo server write again shortly after we vanish.
        await ws.send(b"PUSH-now")
        ws.transport.abort()

    await asyncio.sleep(0.02)
    collected: list[bytes] = []
    async with _open_terminal(_terminal_url(base, token, resume=sid)) as (resumed, _sid):
        try:
            for _ in range(4):
                frame = await asyncio.wait_for(resumed.recv(), timeout=1.0)
                collected.append(frame.encode() if isinstance(frame, str) else bytes(frame))
                if any(b"buffered-output" in blob for blob in collected):
                    break
        except (TimeoutError, ConnectionClosed):
            pass
    assert any(b"buffered-output" in blob for blob in collected), collected


async def test_resume_unknown_session_denied_1008(make_live_gateway: GatewayFactory) -> None:
    base, _ = await make_live_gateway()
    async with ws_connect(_terminal_url(base, _ssh_token(), resume="nope"), open_timeout=5) as ws:
        await _expect_close(ws, 1008)


async def test_resume_expired_denied_1008(make_live_gateway: GatewayFactory) -> None:
    base, _ = await make_live_gateway(resume_ttl_seconds=0.1)
    token = _ssh_token()
    async with _open_terminal(_terminal_url(base, token)) as (ws, sid):
        pass
    await asyncio.sleep(0.35)
    async with ws_connect(_terminal_url(base, token, resume=sid), open_timeout=5) as ws:
        await _expect_close(ws, 1008)


async def test_resume_other_user_denied_1008(make_live_gateway: GatewayFactory) -> None:
    base, _ = await make_live_gateway(resume_ttl_seconds=30.0)
    token_a = _ssh_token(sub="user-1")
    async with _open_terminal(_terminal_url(base, token_a)) as (ws, sid):
        pass
    token_b = _ssh_token(sub="user-2")
    async with ws_connect(_terminal_url(base, token_b, resume=sid), open_timeout=5) as ws:
        await _expect_close(ws, 1008)


async def test_ssh_unreachable_denied_1011(make_live_gateway: GatewayFactory) -> None:
    base, _ = await make_live_gateway(ssh_port=1)  # nothing listens on tcp/1
    async with ws_connect(_terminal_url(base, _ssh_token()), open_timeout=10) as ws:
        await _expect_close(ws, 1011)
