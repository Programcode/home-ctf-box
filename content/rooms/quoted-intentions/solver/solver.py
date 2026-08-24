"""Intended-path solver: derive and submit the CreateProcess resolution chain."""

import httpx

from openrange.content.solver import SolveResult, TaskResult, find_flags

CHAIN = "\n".join(
    [
        r"C:\Program.exe",
        r"C:\Program Files\Unquoted.exe",
        r"C:\Program Files\Unquoted Helper\helper.exe",
    ]
)


def solve(ctx) -> SolveResult:  # type: ignore[no-untyped-def]
    res = httpx.post(f"{ctx.url()}/check", data={"chain": CHAIN}, timeout=10)
    flags = find_flags(res.text)
    captured = flags[0] if flags else None
    detail = None if captured else f"checker rejected the chain: {res.text[:160]}"
    return SolveResult(
        results=[
            TaskResult(
                task_id="order-the-chain",
                ok=bool(captured),
                captured=captured,
                detail=detail,
            )
        ]
    )
