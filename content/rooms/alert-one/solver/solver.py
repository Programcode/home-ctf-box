"""Intended-path solver: triage the queue with the playbook rule."""

import httpx

from openrange.content.solver import SolveResult, TaskResult, find_flags


def solve(ctx) -> SolveResult:  # type: ignore[no-untyped-def]
    expected = ctx.expected_flags["triage-the-queue"]
    flag = None
    detail = None
    with httpx.Client(base_url=ctx.url(), timeout=10) as client:
        queue = client.get("/alerts").json()
        for alert in queue["alerts"]:
            verdict = (
                "true_positive"
                if alert["intel_hit"] and alert["change_ticket"] is None
                else "false_positive"
            )
            res = client.post(
                "/classify",
                json={"alert_id": alert["id"], "verdict": verdict},
            ).json()
            if res.get("queue_status") == "closed":
                flag = res.get("flag")

    captured = flag if flag and find_flags(flag) else None
    ok = captured == expected
    if not ok:
        detail = f"queue did not close cleanly, last response flag={flag!r}"
    return SolveResult(
        results=[TaskResult(task_id="triage-the-queue", ok=ok, captured=captured, detail=detail)]
    )
