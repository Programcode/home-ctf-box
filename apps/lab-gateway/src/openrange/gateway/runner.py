"""Runner API client: interface plus HTTP implementation.

The gateway never talks to Docker. It resolves opaque instance ids to
upstream addresses by asking the runner (``RUNNER_URL``) for
``GET /labs/{instance_id}/address``, authenticated as a service per
docs/contracts/runner-api.md. The Protocol exists so tests substitute a
fake without an HTTP layer.
"""

from __future__ import annotations

import hashlib
import hmac
import time
from dataclasses import dataclass
from typing import Any, Protocol

import httpx

ADDRESS_PATH_TEMPLATE = "/labs/{instance_id}/address"


class RunnerUnavailableError(Exception):
    """Runner unreachable or answering with a server error."""


class InstanceNotFoundError(Exception):
    """Runner reports no such lab instance."""


@dataclass(frozen=True)
class RunnerAddress:
    """Upstream host for a lab instance."""

    host: str


class RunnerClient(Protocol):
    async def instance_address(self, instance_id: str) -> RunnerAddress:
        """Resolve an instance id to its upstream address."""
        ...

    async def ping(self) -> bool:
        """Return whether the runner is reachable."""
        ...


def service_auth_headers(service_token: str, body: bytes = b"") -> dict[str, str]:
    """Build runner service headers: timestamp + HMAC over ``{ts}:{body}``."""
    timestamp = str(int(time.time()))
    digest = hmac.new(
        service_token.encode(), timestamp.encode() + b":" + body, hashlib.sha256
    ).hexdigest()
    return {"X-Runner-Timestamp": timestamp, "X-Runner-Signature": digest}


class HttpRunnerClient:
    """Concrete RunnerClient speaking the runner API over HTTP."""

    def __init__(self, runner_url: str, service_token: str, timeout_seconds: float = 5.0) -> None:
        self._base_url = runner_url.rstrip("/")
        self._service_token = service_token
        self._timeout_seconds = timeout_seconds

    async def _get(self, path: str) -> httpx.Response:
        headers = service_auth_headers(self._service_token) if self._service_token else {}
        try:
            async with httpx.AsyncClient(
                base_url=self._base_url, timeout=self._timeout_seconds
            ) as client:
                return await client.get(path, headers=headers)
        except httpx.HTTPError as exc:
            raise RunnerUnavailableError("runner request failed") from exc

    async def instance_address(self, instance_id: str) -> RunnerAddress:
        response = await self._get(ADDRESS_PATH_TEMPLATE.format(instance_id=instance_id))
        if response.status_code == 404:
            raise InstanceNotFoundError(instance_id)
        if response.status_code != 200:
            raise RunnerUnavailableError(f"runner returned {response.status_code}")
        try:
            payload: dict[str, Any] = response.json()
        except ValueError as exc:
            raise RunnerUnavailableError("runner sent invalid address payload") from exc
        host = payload.get("host")
        if not isinstance(host, str) or not host:
            raise RunnerUnavailableError("runner sent invalid address payload")
        return RunnerAddress(host=host)

    async def ping(self) -> bool:
        try:
            response = await self._get("/healthz")
        except RunnerUnavailableError:
            return False
        return response.status_code == 200
