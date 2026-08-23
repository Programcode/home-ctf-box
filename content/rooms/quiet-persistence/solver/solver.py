"""Intended-path solver: sweep persistence locations, file the findings report."""

import json
import urllib.parse

import paramiko

from openrange.content.solver import SolveResult, TaskResult, find_flags

SWEEPS = {
    "/etc/cron.d": "ls -1 /etc/cron.d",
    "/usr/local/sbin": "ls -1 /usr/local/sbin",
}
GREPS = [
    "grep -l beacon.log /home/*/.bashrc 2>/dev/null || true",
    "ls -1 /etc/systemd/system/*.service 2>/dev/null || true",
]
REPORT_PATH = "/api/report"


def _target(ctx) -> tuple[str, int]:  # type: ignore[no-untyped-def]
    parsed = urllib.parse.urlsplit(ctx.url("target"))
    return parsed.hostname or "target", parsed.port or 22


def _run(client: paramiko.SSHClient, cmd: str, timeout: int = 25) -> str:
    _, stdout, _stderr = client.exec_command(cmd, timeout=timeout)
    return stdout.read().decode(errors="replace")


def _paths(raw: str) -> list[str]:
    return [line.strip() for line in raw.splitlines() if line.strip().startswith("/")]


def solve(ctx) -> SolveResult:  # type: ignore[no-untyped-def]
    host, port = _target(ctx)
    captured = None
    detail = None
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        host,
        port=port,
        username="analyst",
        password="analyst",
        look_for_keys=False,
        allow_agent=False,
        timeout=15,
    )
    try:
        findings: list[str] = []
        for directory, sweep in SWEEPS.items():
            for line in _run(client, sweep).splitlines():
                if line.strip() and not line.startswith("ls:"):
                    findings.append(f"{directory}/{line.strip()}")
        for grep in GREPS:
            findings.extend(_paths(_run(client, grep)))
        findings = list(dict.fromkeys(findings))
        if len(findings) < 4:
            detail = f"sweeps surfaced only {len(findings)} artifacts"

        report_cmd = (
            "python3 -c "
            "'import json,urllib.request;"
            f'req=urllib.request.Request("http://127.0.0.1:8000{REPORT_PATH}",'
            'data=json.dumps({"findings": ' + json.dumps(findings) + "}).encode(),"
            'headers={"Content-Type": "application/json"});'
            "print(urllib.request.urlopen(req).read().decode())'"
        )
        response = _run(client, report_cmd)
        try:
            verdict = json.loads(response)
        except json.JSONDecodeError:
            verdict = {}
        flags = find_flags(response)
        if verdict.get("status") == "verified" and flags:
            captured = flags[0]
            detail = f"report verified all {len(findings)} submitted artifacts"
        elif not detail:
            detail = f"report not verified: matched {verdict.get('matched')} of {verdict.get('expected_total')}"
    finally:
        client.close()

    return SolveResult(
        results=[
            TaskResult(
                task_id="report-artifacts",
                ok=captured is not None,
                captured=captured,
                detail=detail,
            )
        ]
    )
