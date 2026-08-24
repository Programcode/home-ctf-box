"""Intended-path solver: author the four detections and validate them on the forge."""

import re

import httpx

from openrange.content.solver import SolveResult, TaskResult

RULESET = {
    "sqli-union-select": r"\bUNION\b[\s+]+(?:ALL[\s+]+)?SELECT\b",
    "path-traversal": r"(?:\.\.[/\\]){2,}|%2e%2e(?:%2f|[\\/])",
    "exfil-base64-param": r"[?&](?:d|c|cmd|blob)=[A-Za-z0-9+/]{16,}={0,2}",
    "dns-tunnel-label": r"\b[A-Za-z0-9]{40,}\.",
}


def solve(ctx) -> SolveResult:  # type: ignore[no-untyped-def]
    expected = ctx.expected_flags["ship-the-ruleset"]
    with httpx.Client(base_url=ctx.url(), timeout=10) as client:
        bundle = client.get("/evidence/traces.json").json()
        assert set(bundle) == set(RULESET), "trace bundle rule ids drifted"

        # Sanity check the authored rules against the published fixtures
        # exactly like the validator will.
        for rid, pattern in RULESET.items():
            compiled = re.compile(pattern, re.IGNORECASE)
            assert all(compiled.search(s) for s in bundle[rid]["positives"]), rid
            assert not any(compiled.search(s) for s in bundle[rid]["negatives"]), rid

        res = client.post("/forge", json={"rules": RULESET})
        payload = res.json()

    captured = payload.get("flag")
    ok = bool(payload.get("solved")) and captured == expected
    detail = None if ok else str(payload)[:300]
    return SolveResult(
        results=[TaskResult(task_id="ship-the-ruleset", ok=ok, captured=captured, detail=detail)]
    )
