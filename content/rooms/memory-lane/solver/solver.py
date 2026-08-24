"""Intended-path solver: parse both artifacts and report the triple."""

from collections import Counter
from urllib.parse import urlparse

import httpx

from openrange.content.solver import SolveResult, TaskResult


def solve(ctx) -> SolveResult:  # type: ignore[no-untyped-def]
    expected = ctx.expected_flags["catch-the-injection"]
    with httpx.Client(base_url=ctx.url(), timeout=10) as client:
        listing = client.get("/evidence/processes.txt").text
        excerpt = client.get("/evidence/strings-excerpt.txt").text

    pids = set()
    suspicious = None
    for line in listing.splitlines()[1:]:
        columns = line.split(None, 6)
        if len(columns) < 7:
            continue
        pid, ppid, args = columns[0], columns[1], columns[6].strip()
        pids.add(pid)
        if args.startswith("/tmp/") and suspicious is None:
            suspicious = (args.split(" ")[0], ppid)

    if suspicious is None:
        return SolveResult(
            results=[
                TaskResult(
                    task_id="catch-the-injection",
                    ok=False,
                    detail="no /tmp executable found in process listing",
                )
            ]
        )

    process_path, parent_pid = suspicious
    if parent_pid in pids:
        return SolveResult(
            results=[
                TaskResult(
                    task_id="catch-the-injection",
                    ok=False,
                    detail=f"parent {parent_pid} exists in dump; anomaly logic failed",
                )
            ]
        )

    hosts = Counter()
    for line in excerpt.splitlines():
        if line.startswith("Host: "):
            host = line[len("Host: ") :].strip()
            hosts[urlparse(f"//{host}").hostname or host] += 1

    if not hosts:
        return SolveResult(
            results=[
                TaskResult(
                    task_id="catch-the-injection",
                    ok=False,
                    detail="no Host headers found in strings excerpt",
                )
            ]
        )

    c2_domain = hosts.most_common(1)[0][0]
    res = httpx.post(
        f"{ctx.url()}/report",
        json={
            "process_path": process_path,
            "parent_pid": parent_pid,
            "c2_domain": c2_domain,
        },
        timeout=10,
    )
    captured = res.json().get("flag") if res.is_success else None
    ok = bool(captured) and captured == expected
    detail = None if ok else f"report rejected: {process_path=} {parent_pid=} {c2_domain=}"
    return SolveResult(
        results=[TaskResult(task_id="catch-the-injection", ok=ok, captured=captured, detail=detail)]
    )
