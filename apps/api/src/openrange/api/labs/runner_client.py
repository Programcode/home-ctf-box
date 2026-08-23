"""Authenticated client for the runner agent (docs/contracts/runner-api.md)."""

from __future__ import annotations

import base64
import hashlib
import hmac
import io
import os
import tarfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import httpx

RunnerState = Literal["ready", "starting", "stopped", "missing"]


class RunnerError(Exception):
    def __init__(self, status: int, detail: str) -> None:
        super().__init__(detail)
        self.status = status
        self.detail = detail


def sign(token: str, body: bytes, timestamp: int) -> str:
    message = f"{timestamp}:".encode() + body
    return hmac.new(token.encode(), message, hashlib.sha256).hexdigest()


@dataclass(slots=True)
class InstanceHandle:
    instance_id: str
    state: str
    network: str
    targets: list[dict[str, str]]


class RunnerClient:
    def __init__(self, base_url: str | None = None, token: str | None = None) -> None:
        self.base_url = base_url or os.environ.get(
            "OPENRANGE_RUNNER_API_URL", "http://localhost:8771"
        )
        self.token = token or os.environ.get("OPENRANGE_RUNNER_API_TOKEN", "")

    def _headers(self, body: bytes) -> dict[str, str]:
        ts = int(time.time())
        headers = {
            "x-runner-timestamp": str(ts),
            "x-runner-signature": sign(self.token, body, ts),
        }
        if body:
            headers["content-type"] = "application/json"
        return headers

    async def _call(self, method: str, path: str, payload: Any) -> Any:
        import json as jsonlib

        body = b"" if payload is None else jsonlib.dumps(payload).encode()
        async with httpx.AsyncClient(base_url=self.base_url, timeout=90) as client:
            res = await client.request(
                method, path, content=body or None, headers=self._headers(body)
            )
        if res.status_code >= 400:
            try:
                detail = res.json().get("detail", res.text)
            except Exception:
                detail = res.text
            raise RunnerError(res.status_code, str(detail))
        if res.status_code == 204 or not res.content:
            return {}
        data: Any = res.json()
        return data

    @staticmethod
    def pack_context(context_dir: Path) -> str:
        """Tar+gzip a target build context for remote builds."""
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz") as tar:
            for path in sorted(context_dir.rglob("*")):
                if path.is_file():
                    tar.add(path, arcname=path.relative_to(context_dir))
        return base64.b64encode(buf.getvalue()).decode()

    async def create_instance(
        self,
        *,
        instance_id: str,
        image: str | None,
        env: dict[str, str],
        ports: list[int],
        ttl_seconds: int,
        labels: dict[str, str],
        build_context_tar_gz_base64: str | None = None,
        cpus: float = 1.5,
        mem_mb: int = 512,
        pids_limit: int = 256,
    ) -> InstanceHandle:
        payload: dict[str, Any] = {
            "instance_id": instance_id,
            "image": image,
            "env": env,
            "cpus": cpus,
            "mem_mb": mem_mb,
            "pids_limit": pids_limit,
            "ports": ports,
            "ttl_seconds": ttl_seconds,
            "labels": labels,
        }
        if build_context_tar_gz_base64 is not None:
            payload["build_context_tar_gz_base64"] = build_context_tar_gz_base64
        data = await self._call("POST", "/v1/instances", payload)
        return InstanceHandle(
            instance_id=instance_id,
            state=data.get("state", "ready"),
            network=data.get("network", ""),
            targets=list(data.get("targets", [])),
        )

    async def restart(self, instance_id: str) -> dict[str, str]:
        data: dict[str, str] = await self._call("POST", f"/v1/instances/{instance_id}/restart", {})
        return data

    async def delete(self, instance_id: str) -> None:
        await self._call("DELETE", f"/v1/instances/{instance_id}", None)

    async def get(self, instance_id: str) -> dict[str, Any]:
        data: dict[str, Any] = await self._call("GET", f"/v1/instances/{instance_id}", None)
        return data

    async def reconcile(self, known_ids: list[str]) -> dict[str, list[str]]:
        data: dict[str, list[str]] = await self._call(
            "POST", "/v1/reconcile", {"known_instance_ids": known_ids}
        )
        return data
