"""Integration fixtures: real Docker daemon, real app, HMAC-signed HTTP client."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import tempfile
import time
import uuid
from collections.abc import AsyncIterator, Callable, Coroutine, Generator
from pathlib import Path
from typing import Any

import docker
import httpx
import pytest
from docker.errors import ImageNotFound

RUNNER_TOKEN = "integration-runner-token"
FIXTURE_IMAGE = "openrange/test-runner-fixture:latest"

_FIXTURE_APP = """\
from flask import Flask, jsonify

app = Flask(__name__)


@app.get("/healthz")
def healthz():
    return jsonify(status="ok")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
"""

_FIXTURE_DOCKERFILE = """\
FROM python:3.12-alpine
RUN pip install --no-cache-dir 'flask>=3,<4'
COPY app.py /srv/app.py
CMD ["python3", "/srv/app.py"]
"""


def sign_headers(token: str, body: bytes, timestamp: str | int | None = None) -> dict[str, str]:
    issued_at = str(int(time.time()) if timestamp is None else timestamp)
    digest = hmac.new(token.encode(), issued_at.encode() + b":" + body, hashlib.sha256).hexdigest()
    return {"X-Runner-Timestamp": issued_at, "X-Runner-Signature": digest}


class RunnerClient:
    """Async httpx wrapper that signs requests per the runner auth contract."""

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        *,
        timestamp: str | int | None = None,
        signature: str | None = None,
        omit_signature: bool = False,
    ) -> httpx.Response:
        body = json.dumps(payload).encode() if payload is not None else b""
        headers = sign_headers(RUNNER_TOKEN, body, timestamp)
        if omit_signature:
            headers.pop("X-Runner-Signature")
        elif signature is not None:
            headers["X-Runner-Signature"] = signature
        return await self._client.request(
            method, path, content=body, headers=headers | {"content-type": "application/json"}
        )

    async def signed_for_body(self, method: str, path: str, body: bytes) -> httpx.Response:
        return await self._client.request(
            method,
            path,
            content=body,
            headers=sign_headers(RUNNER_TOKEN, body) | {"content-type": "application/json"},
        )

    async def with_headers(
        self, method: str, path: str, *, body: bytes = b"", headers: dict[str, str]
    ) -> httpx.Response:
        return await self._client.request(method, path, content=body, headers=headers)

    async def raw_get(self, path: str) -> httpx.Response:
        return await self._client.get(path)


@pytest.fixture(scope="session")
def _runner_env() -> Generator[None]:
    os.environ.setdefault("OPENRANGE_ENV", "dev")
    os.environ["OPENRANGE_RUNNER_API_TOKEN"] = RUNNER_TOKEN
    yield
    os.environ.pop("OPENRANGE_RUNNER_API_TOKEN", None)


@pytest.fixture(scope="session")
def docker_client() -> Generator[docker.DockerClient]:
    client = docker.from_env()
    yield client
    client.close()


@pytest.fixture(autouse=True)
def _sweep_managed_objects(docker_client: docker.DockerClient) -> Generator[None]:
    yield
    for container in docker_client.containers.list(
        all=True, filters={"label": "openrange.managed=true"}
    ):
        container.remove(force=True)
    for network in docker_client.networks.list(filters={"label": "openrange.managed=true"}):
        network.remove()


@pytest.fixture(scope="session")
def lab_image(docker_client: docker.DockerClient) -> Generator[str]:
    with tempfile.TemporaryDirectory(prefix="openrange-fixture-") as tmp:
        Path(tmp).joinpath("app.py").write_text(_FIXTURE_APP)
        Path(tmp).joinpath("Dockerfile").write_text(_FIXTURE_DOCKERFILE)
        docker_client.images.build(path=tmp, tag=FIXTURE_IMAGE, rm=True)
    yield FIXTURE_IMAGE
    try:
        docker_client.images.remove(FIXTURE_IMAGE, force=True)
    except ImageNotFound:
        pass


@pytest.fixture(scope="session")
async def runner_client(_runner_env: None) -> AsyncIterator[RunnerClient]:
    from openrange.runner.main import create_app

    transport = httpx.ASGITransport(app=create_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://runner.local") as client:
        yield RunnerClient(client)


@pytest.fixture(scope="session")
def make_payload(lab_image: str) -> Callable[..., dict[str, Any]]:
    def factory(**overrides: Any) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "instance_id": str(uuid.uuid4()),
            "image": lab_image,
            "env": {"ROOM_FLAG": "FLAG{integration}"},
            "cpus": 0.5,
            "mem_mb": 256,
            "pids_limit": 128,
            "ports": [8000],
            "ttl_seconds": 900,
            "labels": {"room": "integration"},
        }
        payload.update(overrides)
        return payload

    return factory


CreateInstanceFactory = Callable[..., Coroutine[Any, Any, tuple[str, dict[str, Any]]]]


@pytest.fixture
def create_instance(
    runner_client: RunnerClient, make_payload: Callable[..., dict[str, Any]]
) -> CreateInstanceFactory:
    async def factory(**overrides: Any) -> tuple[str, dict[str, Any]]:
        payload = make_payload(**overrides)
        response = await runner_client.request("POST", "/v1/instances", payload)
        assert response.status_code == 201, response.text
        return payload["instance_id"], response.json()

    return factory
