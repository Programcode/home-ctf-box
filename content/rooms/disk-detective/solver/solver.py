"""Intended-path solver: window the timeline, find both artifacts, report in order."""

import httpx

from openrange.content.solver import SolveResult, TaskResult


def solve(ctx) -> SolveResult:  # type: ignore[no-untyped-def]
    expected = ctx.expected_flags["order-the-findings"]
    with httpx.Client(base_url=ctx.url(), timeout=10) as client:
        timeline = client.get("/evidence/timeline.csv").text

    deleted_rows = []
    cron_rows = []
    for line in timeline.splitlines():
        columns = line.split("|")
        if len(columns) < 11:
            continue
        name, mtime = columns[1], int(columns[8])
        if "(deleted)" in name:
            deleted_rows.append((mtime, name))
        if name.startswith("/etc/cron.d/"):
            cron_rows.append((mtime, name))

    if len(deleted_rows) != 1 or len(cron_rows) != 1:
        return SolveResult(
            results=[
                TaskResult(
                    task_id="order-the-findings",
                    ok=False,
                    detail=f"unexpected artifact counts: {deleted_rows=} {cron_rows=}",
                )
            ]
        )

    deleted_mtime, deleted_name = deleted_rows[0]
    cron_mtime, cron_path = cron_rows[0]
    if deleted_mtime >= cron_mtime:
        return SolveResult(
            results=[
                TaskResult(
                    task_id="order-the-findings",
                    ok=False,
                    detail="chronology check failed; expected deletion before persistence",
                )
            ]
        )

    res = httpx.post(
        f"{ctx.url()}/report",
        json={"findings": [deleted_name, cron_path]},
        timeout=10,
    )
    captured = res.json().get("flag") if res.is_success else None
    ok = bool(captured) and captured == expected
    detail = None if ok else f"report rejected: {deleted_name=} {cron_path=}"
    return SolveResult(
        results=[TaskResult(task_id="order-the-findings", ok=ok, captured=captured, detail=detail)]
    )
