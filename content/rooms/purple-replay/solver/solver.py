"""Intended-path solver: replay every scripted step, tune one rule per stage, finalize."""

import httpx
from openrange.content.solver import SolveResult, TaskResult, find_flags

TASK_ID = "purple-loop"


def solve(ctx) -> SolveResult:  # type: ignore[no-untyped-def]
    base = ctx.url()
    detail = None

    lab = httpx.get(base + "/lab/stages", timeout=10).json()
    attacker_src = str(lab.get("attacker_src", ""))
    if not attacker_src and detail is None:
        detail = "stages document did not name the attacker source address"
        return SolveResult(
            results=[TaskResult(task_id=TASK_ID, ok=False, captured=None, detail=detail)]
        )

    rules: dict[str, dict] = {
        "recon": {
            "match": [{"field": "target", "op": "contains", "value": ".git"}],
            "at_least": 1,
        },
        "brute-force": {
            "match": [
                {"field": "target", "op": "equals", "value": "/victim/login"},
                {"field": "status", "op": "equals", "value": 401},
            ],
            "at_least": 5,
        },
        "exploit": {
            "match": [{"field": "target", "op": "contains", "value": "../"}],
            "at_least": 1,
        },
        "exfil": {
            "match": [{"field": "bytes_in", "op": ">=", "value": 500000}],
            "at_least": 1,
        },
    }

    def _headers() -> dict[str, str]:
        return {"X-Src-Ip": attacker_src}

    for stage in [s["stage"] for s in lab["stages"]]:
        steps = next(s["steps"] for s in lab["stages"] if s["stage"] == stage)
        for step in steps:
            path = str(step["path"])
            method = str(step["method"])
            body = step.get("body") or {}
            if method == "POST":
                reply = httpx.post(base + path, headers=_headers(), json=body, timeout=10)
            else:
                reply = httpx.get(base + path, headers=_headers(), timeout=10)
            if reply.status_code >= 500 and detail is None:
                detail = f"{stage} replay step failed: {reply.status_code}"
        gate = httpx.post(
            base + "/lab/detect",
            json={"stage": stage, "rule": rules[stage]},
            timeout=10,
        )
        if gate.status_code != 200 and detail is None:
            detail = f"gate rejected rule for {stage}: {gate.json()}"

    final = httpx.post(base + "/lab/finalize", json={}, timeout=10).json()
    flags = find_flags(final.get("flag") or "")
    captured = flags[0] if final.get("finalized") and flags else None
    if captured is None and detail is None:
        detail = f"finalize refused: {final}"

    return SolveResult(
        results=[
            TaskResult(task_id=TASK_ID, ok=captured is not None, captured=captured, detail=detail)
        ]
    )
