"""Intended-path solver: grep the access log the way the lesson teaches."""

from collections import Counter

import httpx

from openrange.content.solver import SolveResult, TaskResult, find_flags


def solve(ctx) -> SolveResult:  # type: ignore[no-untyped-def]
    expected = ctx.expected_flags["name-the-intruder"]
    with httpx.Client(base_url=ctx.url(), timeout=30) as client:
        log_text = client.get("/evidence/access.log").text

    sqli_hits = Counter()
    success_line = None
    for line in log_text.splitlines():
        if "sqlmap" in line:
            sqli_hits[line.split(" ", 1)[0]] += 1
        if '"POST /login' in line and " 302 " in line:
            success_line = line

    if not sqli_hits or success_line is None:
        return SolveResult(
            results=[
                TaskResult(
                    task_id="name-the-intruder",
                    ok=False,
                    detail="could not locate sweep or successful login in log",
                )
            ]
        )

    sqli_ip = sqli_hits.most_common(1)[0][0]
    user_part = success_line.split("?user=", 1)[1]
    account = user_part.split(" ", 1)[0]
    login_agent = success_line.rsplit('"', 2)[-2]

    res = httpx.post(
        f"{ctx.url()}/report",
        json={"sqli_ip": sqli_ip, "account": account, "login_agent": login_agent},
        timeout=10,
    )
    captured = res.json().get("flag") if res.is_success else None
    ok = bool(captured) and find_flags(captured) != [] and captured == expected
    detail = None if ok else f"report rejected: {sqli_ip=} {account=} {login_agent=}"
    return SolveResult(
        results=[TaskResult(task_id="name-the-intruder", ok=ok, captured=captured, detail=detail)]
    )
