"""Intended-path solver: SSH as learner and read the home directory flag."""

import urllib.parse

import paramiko

from openrange.content.solver import SolveResult, TaskResult, find_flags


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
        _, stdout, stderr = client.exec_command("cat /home/learner/flag.txt", timeout=15)
        out = stdout.read().decode(errors="replace")
        err = stderr.read().decode(errors="replace")
    finally:
        client.close()
    flags = find_flags(out)
    captured = flags[0] if flags else None
    return SolveResult(
        results=[
            TaskResult(
                task_id="first-login",
                ok=bool(captured),
                captured=captured,
                detail=None if captured else f"no flag in file output: {out[:200]} {err[:200]}",
            )
        ]
    )
