"""Gateway test fixtures: fake runner, aiohttp echo target, asyncssh echo server."""

from __future__ import annotations

import asyncio
import socket
from collections.abc import AsyncIterator, Callable
from typing import Any

import asyncssh
import httpx
import pytest
from aiohttp import web
from fastapi import FastAPI
from openrange.gateway.config import GatewaySettings
from openrange.gateway.main import create_app
from openrange.gateway.runner import (
    InstanceNotFoundError,
    RunnerAddress,
    RunnerUnavailableError,
)
from openrange.gateway.tokens import mint_token

SECRET = "test-gateway-secret"
LAB_ID = "lab-1a2b3c4d"
SSH_USERNAME = "labuser"
SSH_PASSWORD = "labpass"

_BACKGROUND_TASKS: set[asyncio.Task[None]] = set()


class FakeRunner:
    """In-memory RunnerClient stand-in for tests."""

    def __init__(self) -> None:
        self.addresses: dict[str, str] = {}
        self.fail = False

    async def instance_address(self, instance_id: str) -> RunnerAddress:
        if self.fail:
            raise RunnerUnavailableError("runner down")
        host = self.addresses.get(instance_id)
        if host is None:
            raise InstanceNotFoundError(instance_id)
        return RunnerAddress(host=host)

    async def ping(self) -> bool:
        return not self.fail


async def _echo_handler(request: web.Request) -> web.Response:
    if request.path.endswith("/headers"):
        return web.json_response(
            {
                "query_keys": sorted(set(request.rel_url.query.keys())),
                "x_forwarded_for": request.headers.get("X-Forwarded-For"),
                "x_forwarded_proto": request.headers.get("X-Forwarded-Proto"),
                "x_forwarded_host": request.headers.get("X-Forwarded-Host"),
                "x_forwarded_port": request.headers.get("X-Forwarded-Port"),
                "authorization": request.headers.get("Authorization"),
                "cookie": request.headers.get("Cookie"),
            }
        )
    body = await request.content.read()
    return web.Response(body=body)


@pytest.fixture
def fake_runner() -> FakeRunner:
    runner = FakeRunner()
    runner.addresses[LAB_ID] = "127.0.0.1"
    return runner


@pytest.fixture
async def echo_target() -> AsyncIterator[tuple[str, int]]:
    app = web.Application()
    app.router.add_route("*", "/{tail:.*}", _echo_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    assert runner.addresses
    port = runner.addresses[0][1]
    yield ("127.0.0.1", port)
    await runner.cleanup()


class EchoSession(asyncssh.SSHServerSession):
    """asyncssh server session echoing bytes back over a PTY."""

    def __init__(self, resizes: list[tuple[int, int]]) -> None:
        self._resizes = resizes
        self._chan: Any = None

    def connection_made(self, chan: Any) -> None:
        self._chan = chan

    def pty_requested(
        self,
        term_type: str,
        term_size: tuple[int, int, int, int],
        term_modes: dict[int, int],
    ) -> bool:
        return True

    def shell_requested(self) -> bool:
        return True

    def terminal_size_changed(self, width: int, height: int, pixwidth: int, pixheight: int) -> None:
        self._resizes.append((width, height))

    def data_received(self, data: str | bytes, datatype: int = 0) -> None:
        assert self._chan is not None
        payload = data.encode() if isinstance(data, str) else data
        if payload.startswith(b"PUSH"):
            task = asyncio.create_task(_delayed_write(self._chan))
            _BACKGROUND_TASKS.add(task)
            task.add_done_callback(_BACKGROUND_TASKS.discard)
        self._chan.write(payload)

    def eof_received(self) -> None:
        if self._chan is not None:
            self._chan.close()


async def _delayed_write(chan: Any) -> None:
    await asyncio.sleep(0.05)
    chan.write(b"buffered-output")


class EchoSshServer(asyncssh.SSHServer):
    """Password-authenticated server handing out echo sessions."""

    def __init__(self, resizes: list[tuple[int, int]]) -> None:
        self._resizes = resizes

    def password_auth_supported(self) -> bool:
        return True

    def validate_password(self, username: str, password: str) -> bool:
        return username == SSH_USERNAME and password == SSH_PASSWORD

    def session_requested(self) -> EchoSession:
        return EchoSession(self._resizes)


@pytest.fixture
async def ssh_target() -> AsyncIterator[tuple[int, list[tuple[int, int]]]]:
    resizes: list[tuple[int, int]] = []
    host_key = asyncssh.generate_private_key("ssh-ed25519")
    server = await asyncssh.listen(
        "127.0.0.1",
        0,
        family=socket.AF_INET,
        server_host_keys=[host_key],
        server_factory=lambda: EchoSshServer(resizes),
        line_editor=False,
        line_echo=False,
        encoding=None,
    )
    port = server.sockets[0].getsockname()[1]
    yield (port, resizes)
    server.close()
    await server.wait_closed()


@pytest.fixture
def make_settings(
    echo_target: tuple[str, int], ssh_target: tuple[int, list[tuple[int, int]]]
) -> Callable[..., GatewaySettings]:
    def factory(**overrides: Any) -> GatewaySettings:
        values: dict[str, Any] = {
            "gateway_secret": SECRET,
            "runner_url": "http://runner.test",
            "runner_service_token": "",
            "max_sessions_per_lab": 4,
            "resume_ttl_seconds": 60.0,
            "ssh_port": ssh_target[0],
            "ssh_user": SSH_USERNAME,
            "ssh_password": SSH_PASSWORD,
        }
        values.update(overrides)
        return GatewaySettings(**values)

    return factory


@pytest.fixture
def mint(make_settings: Callable[..., GatewaySettings]) -> Callable[..., str]:
    settings = make_settings()

    def factory(**overrides: Any) -> str:
        params: dict[str, Any] = {
            "secret": settings.gateway_secret,
            "sub": "user-1",
            "lab": LAB_ID,
            "ports": [8000],
            "ssh": False,
        }
        params.update(overrides)
        return mint_token(**params)

    return factory


@pytest.fixture
def build_gateway(
    make_settings: Callable[..., GatewaySettings], fake_runner: FakeRunner
) -> Callable[..., FastAPI]:
    def factory(**overrides: Any) -> FastAPI:
        return create_app(settings=make_settings(**overrides), runner=fake_runner)

    return factory


@pytest.fixture
async def gateway_app(build_gateway: Callable[..., FastAPI]) -> AsyncIterator[FastAPI]:
    app = build_gateway()
    async with app.router.lifespan_context(app):
        yield app


@pytest.fixture
async def client(gateway_app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=gateway_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://gateway.test") as http:
        yield http
