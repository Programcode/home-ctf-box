"""Intended-path solver: version analysis, note-based elimination, simulation."""

import re
import urllib.parse

import httpx
import paramiko

from openrange.content.solver import SolveResult, TaskResult, find_flags

CANDIDATE_RE = re.compile(r"CVE-\d{4}-\d{4,7}")
VERDICT_RE = re.compile(r"VERDICT:\s*(not applicable|applicable)")
SYSINFO_PORT = 8000


def _target(ctx) -> tuple[str, int]:  # type: ignore[no-untyped-def]
    parsed = urllib.parse.urlsplit(ctx.url("target"))
    return parsed.hostname or "target", parsed.port or 22


def solve(ctx) -> SolveResult:  # type: ignore[no-untyped-def]
    host, port = _target(ctx)
    captured = None
    detail = None

    sysinfo = httpx.get(f"http://{host}:{SYSINFO_PORT}/api/sysinfo", timeout=10)
    if "5.4.0-42" not in sysinfo.text:
        detail = "sysinfo endpoint did not report the expected simulated kernel"

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        host,
        port=port,
        username="learner",
        password="learner",
        look_for_keys=False,
        allow_agent=False,
        timeout=15,
    )
    try:
        _, stdout, _stderr = client.exec_command("cat /opt/exploit-sim/NOTES.md", timeout=15)
        notes = stdout.read().decode(errors="replace")

        chosen = None
        for block in re.split(r"(?=Candidate [A-C])", notes):
            verdict = VERDICT_RE.search(block)
            cve = CANDIDATE_RE.search(block)
            if verdict and cve and verdict.group(1) == "applicable":
                chosen = cve.group(0)
                break
        if chosen is None:
            detail = "no applicable candidate found in the notes"
            return SolveResult(
                results=[TaskResult(task_id="pick-the-cve", ok=False, detail=detail)]
            )

        _, stdout, stderr = client.exec_command(
            f"/usr/local/bin/exploit-sim --simulate {chosen}", timeout=20
        )
        out = stdout.read().decode(errors="replace")
        err = stderr.read().decode(errors="replace")
    finally:
        client.close()

    flags = find_flags(out)
    if flags:
        captured = flags[0]
        detail = f"simulator accepted {chosen} after precondition validation"
    elif not detail:
        detail = f"simulator rejected {chosen}: {out[:120]} {err[:120]}"

    return SolveResult(
        results=[
            TaskResult(
                task_id="pick-the-cve",
                ok=captured is not None,
                captured=captured,
                detail=detail,
            )
        ]
    )
