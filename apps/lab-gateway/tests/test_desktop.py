"""Desktop bridge tests against a live uvicorn instance and a TCP RFB-ish echo server."""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import hmac
import json
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any
from urllib.parse import urlencode

import pytest
import uvicorn
from fastapi import FastAPI
from openrange.gateway.desktop import HttpVpnHeartbeatClient, resolve_desktop_port
from openrange.gateway.tokens import mint_token
from websockets.asyncio.client import ClientConnection
from websockets.asyncio.client import connect as ws_connect
from websockets.exceptions import ConnectionClosed

LAB_ID = "lab-1a2b3c4d"
SECRET = "test-gateway-secret"

GatewayFactory = Callable[..., Awaitable[tuple[str, FastAPI]]]


async def _echo_handler(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    try:
        while True:
            chunk = await reader.read(8192)
            if not chunk:
                break
            writer.write(chunk)
            await writer.drain()
    finally:
        writer.close()


@pytest.fixture
async def rfb_target() -> AsyncIterator[int]:
    """Plain TCP echo standing in for an RFB server."""
    server = await asyncio.start_server(_echo_handler, "127.0.0.1", 0)
    port = int(server.sockets[0].getsockname()[1])
    yield port
    server.close()
    await server.wait_closed()


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


def _desktop_url(
    base: str, token: str, *, port: int | None = None, resume: str | None = None
) -> str:
    params: dict[str, str] = {"token": token}
    if port is not None:
        params["port"] = str(port)
    if resume is not None:
        params["resume"] = resume
    return f"{base}/desktop/{LAB_ID}?{urlencode(params)}"


def _rfb_token(rfb_port: int, **overrides: Any) -> str:
    params: dict[str, Any] = {
        "secret": SECRET,
        "sub": "user-1",
        "lab": LAB_ID,
        "ports": [rfb_port],
        "ssh": False,
    }
    params.update(overrides)
    return str(mint_token(**params))


@contextlib.asynccontextmanager
async def _open_desktop(url: str) -> AsyncIterator[tuple[ClientConnection, str]]:
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


async def test_binary_echo_roundtrip(make_live_gateway: GatewayFactory, rfb_target: int) -> None:
    base, _app = await make_live_gateway()
    url = _desktop_url(base, _rfb_token(rfb_target), port=rfb_target)
    async with _open_desktop(url) as (ws, session_id):
        assert session_id
        payload = b"RFB 003.008\n"
        await ws.send(payload)
        assert await asyncio.wait_for(ws.recv(), timeout=5) == payload
        await ws.send(b"second-chunk")
        assert await asyncio.wait_for(ws.recv(), timeout=5) == b"second-chunk"


async def test_clean_close_control_frame(
    make_live_gateway: GatewayFactory, rfb_target: int
) -> None:
    base, _ = await make_live_gateway()
    url = _desktop_url(base, _rfb_token(rfb_target), port=rfb_target)
    async with ws_connect(url, open_timeout=5) as ws:
        await asyncio.wait_for(ws.recv(), timeout=5)
        await ws.send(json.dumps({"type": "close"}))
        await _expect_close(ws, 1000)


async def test_invalid_token_denied_1008(make_live_gateway: GatewayFactory) -> None:
    base, _ = await make_live_gateway()
    async with ws_connect(_desktop_url(base, "lab-v1.bogus.bogus"), open_timeout=5) as ws:
        await _expect_close(ws, 1008)


async def test_wrong_lab_denied_1008(make_live_gateway: GatewayFactory, rfb_target: int) -> None:
    base, _ = await make_live_gateway()
    other = f"{base}/desktop/lab-other?" + urlencode(
        {"token": _rfb_token(rfb_target), "port": str(rfb_target)}
    )
    async with ws_connect(other, open_timeout=5) as ws:
        await _expect_close(ws, 1008)


async def test_disallowed_port_denied_1008(
    make_live_gateway: GatewayFactory, rfb_target: int
) -> None:
    base, _ = await make_live_gateway()
    # Token allows only 5900; asking for the echo port must be refused.
    url = _desktop_url(base, _rfb_token(5900), port=rfb_target)
    async with ws_connect(url, open_timeout=5) as ws:
        await _expect_close(ws, 1008)


async def test_default_port_is_5900(make_live_gateway: GatewayFactory) -> None:
    base, _ = await make_live_gateway()
    # Token allows 5900 only and nothing listens there: dial happens on the
    # default port and fails as upstream-unavailable, proving the default.
    try:
        probe_reader, probe_writer = await asyncio.wait_for(  # noqa: F841 - probe only
            asyncio.open_connection("127.0.0.1", 5900), timeout=0.5
        )
    except OSError:
        pass
    else:
        probe_writer.close()
        with contextlib.suppress(Exception):
            await probe_writer.wait_closed()
        pytest.skip("host already has a listener on 5900; default-port dial is not observable")
    url = _desktop_url(base, _rfb_token(5900))
    async with ws_connect(url, open_timeout=5) as ws:
        await _expect_close(ws, 1011)


async def test_malformed_port_denied_1008(
    make_live_gateway: GatewayFactory, rfb_target: int
) -> None:
    base, _ = await make_live_gateway()
    url = _desktop_url(base, _rfb_token(rfb_target), port=rfb_target) + "&port=not-a-port"
    async with ws_connect(url, open_timeout=5) as ws:
        await _expect_close(ws, 1008)


def test_resolve_desktop_port_validation() -> None:
    assert resolve_desktop_port(None) == 5900
    assert resolve_desktop_port("5901") == 5901
    for bad in ("abc", "0", "70000", "-1"):
        with pytest.raises(ValueError):
            resolve_desktop_port(bad)


async def test_unknown_instance_denied_1008(
    make_live_gateway: GatewayFactory, rfb_target: int
) -> None:
    base, _ = await make_live_gateway()
    token = _rfb_token(rfb_target)
    other = f"{base}/desktop/lab-missing?" + urlencode({"token": token, "port": str(rfb_target)})
    async with ws_connect(other, open_timeout=5) as ws:
        await _expect_close(ws, 1008)


async def test_concurrency_cap_returns_1013_and_evicts_grace(
    make_live_gateway: GatewayFactory, rfb_target: int
) -> None:
    base, _ = await make_live_gateway(max_sessions_per_lab=1)
    token = _rfb_token(rfb_target)

    async with _open_desktop(_desktop_url(base, token, port=rfb_target)) as (_ws, first_sid):
        async with ws_connect(_desktop_url(base, token, port=rfb_target), open_timeout=5) as second:
            await _expect_close(second, 1013)

    # The closed session sits in the reconnect-grace window, but a new
    # opener wins the slot by evicting it.
    async with _open_desktop(_desktop_url(base, token, port=rfb_target)) as (_third, third_sid):
        assert third_sid != first_sid
        with pytest.raises(ConnectionClosed) as excinfo:
            async with ws_connect(
                _desktop_url(base, token, port=rfb_target, resume=first_sid), open_timeout=5
            ) as stale:
                await asyncio.wait_for(stale.recv(), timeout=5)
        assert excinfo.value.rcvd is not None
        assert excinfo.value.rcvd.code == 1008


async def test_resume_within_grace_reuses_session(
    make_live_gateway: GatewayFactory, rfb_target: int
) -> None:
    base, _ = await make_live_gateway(resume_ttl_seconds=30.0)
    token = _rfb_token(rfb_target)
    async with _open_desktop(_desktop_url(base, token, port=rfb_target)) as (ws, sid):
        await ws.send(b"before-drop")
        assert await asyncio.wait_for(ws.recv(), timeout=5) == b"before-drop"
        ws.transport.abort()  # simulate a hard network drop, not a clean close

    await asyncio.sleep(0.35)
    async with _open_desktop(_desktop_url(base, token, port=rfb_target, resume=sid)) as (
        resumed,
        sid2,
    ):
        assert sid2 == sid
        await resumed.send(b"after-resume")
        assert await asyncio.wait_for(resumed.recv(), timeout=5) == b"after-resume"


async def test_resume_other_user_denied_1008(
    make_live_gateway: GatewayFactory, rfb_target: int
) -> None:
    base, _ = await make_live_gateway(resume_ttl_seconds=30.0)
    token_a = _rfb_token(rfb_target, sub="user-1")
    async with _open_desktop(_desktop_url(base, token_a, port=rfb_target)) as (_ws, sid):
        pass
    token_b = _rfb_token(rfb_target, sub="user-2")
    async with ws_connect(
        _desktop_url(base, token_b, port=rfb_target, resume=sid), open_timeout=5
    ) as ws:
        await _expect_close(ws, 1008)


async def test_resume_unknown_session_denied_1008(
    make_live_gateway: GatewayFactory, rfb_target: int
) -> None:
    base, _ = await make_live_gateway()
    async with ws_connect(
        _desktop_url(base, _rfb_token(rfb_target), port=rfb_target, resume="nope"),
        open_timeout=5,
    ) as ws:
        await _expect_close(ws, 1008)


# --- VPN heartbeat client ---------------------------------------------------

CAPTURE_SECRET = "s3cret"


@pytest.fixture
async def api_capture() -> AsyncIterator[tuple[str, dict[str, Any]]]:
    """API stand-in for /internal/vpn/heartbeat; verifies the gateway HMAC."""
    captured: dict[str, Any] = {}

    async def handler(request: Any) -> Any:
        from aiohttp import web

        body = await request.content.read()
        captured["path"] = request.path
        captured["headers"] = dict(request.headers)
        captured["body"] = body
        timestamp = request.headers.get("X-Gateway-Timestamp")
        signature = request.headers.get("X-Gateway-Signature")
        if timestamp is None or signature is None:
            return web.json_response({"detail": "missing headers"}, status=401)
        expected = hmac.new(
            CAPTURE_SECRET.encode(), timestamp.encode() + b":" + body, hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(expected, signature):
            return web.json_response({"detail": "invalid signature"}, status=401)
        return web.json_response({"ok": True})

    from aiohttp import web

    app = web.Application()
    app.router.add_post("/internal/vpn/heartbeat", handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    assert runner.addresses
    port = runner.addresses[0][1]
    yield f"http://127.0.0.1:{port}", captured
    await runner.cleanup()


async def test_heartbeat_client_signs_and_posts(api_capture: tuple[str, dict[str, Any]]) -> None:
    base, captured = api_capture
    client = HttpVpnHeartbeatClient(api_url=base, secret=CAPTURE_SECRET)
    assert await client.beat("DEVICE-KEY") is True

    assert captured["path"] == "/internal/vpn/heartbeat"
    body: bytes = captured["body"]
    timestamp = captured["headers"]["X-Gateway-Timestamp"]
    expected = hmac.new(
        CAPTURE_SECRET.encode(), timestamp.encode() + b":" + body, hashlib.sha256
    ).hexdigest()
    assert captured["headers"]["X-Gateway-Signature"] == expected
    assert json.loads(body) == {"device_public_key": "DEVICE-KEY"}


async def test_heartbeat_client_reports_rejection_and_outage(
    api_capture: tuple[str, dict[str, Any]],
) -> None:
    base, _captured = api_capture

    # A wrong-secret request is rejected by the API's HMAC check.
    rejecting = HttpVpnHeartbeatClient(api_url=base, secret="not-the-secret")
    assert await rejecting.beat("DEVICE-KEY") is False

    # Connection failures surface as False, never exceptions.
    dead = HttpVpnHeartbeatClient(api_url="http://127.0.0.1:1", secret=CAPTURE_SECRET)
    assert await dead.beat("DEVICE-KEY") is False
