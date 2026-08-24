"""Intended-path solver: reconstruct the leaked key chain from the log."""

import httpx

from openrange.content.solver import SolveResult, TaskResult, find_flags


def solve(ctx) -> SolveResult:  # type: ignore[no-untyped-def]
    base = ctx.url()
    log = httpx.get(f"{base}/evidence/cloudtrail-sim.json", timeout=10).json()
    events = log["events"]

    q1 = next(e["userIdentity"]["userName"] for e in events if e["eventName"] == "assume_role")
    mint = next(e for e in events if e["eventName"] == "create_access_key")
    q2 = mint["requestParameters"]["userName"]
    exposure = next(
        e
        for e in events
        if any(
            stmt.get("Principal") == "*"
            for stmt in (e.get("responseElements") or {}).get("policy", {}).get("Statement", [])
        )
    )
    q3 = exposure["eventName"]

    res = httpx.get(
        f"{base}/report",
        params={"q1": q1, "q2": q2, "q3": q3},
        timeout=10,
    )
    flags = find_flags(res.text)
    captured = flags[0] if flags else None
    return SolveResult(
        results=[
            TaskResult(
                task_id="reconstruct-key-chain",
                ok=bool(captured),
                captured=captured,
                detail=None if captured else "report desk did not accept the answers",
            )
        ]
    )
