"""Intended-path solver: regex injection against a fixed subject."""

import httpx

from openrange.content.solver import SolveResult, TaskResult, find_flags

PATTERN = ".*"


def solve(ctx) -> SolveResult:  # type: ignore[no-untyped-def]
    res = httpx.post(f"{ctx.url()}/unlock", data={"code": PATTERN}, timeout=10)
    flags = find_flags(res.text)
    captured = flags[0] if flags else None
    return SolveResult(
        results=[
            TaskResult(
                task_id="regex-unlock",
                ok=bool(captured),
                captured=captured,
                detail=None if captured else "no flag in response",
            )
        ]
    )
