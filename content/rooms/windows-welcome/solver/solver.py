"""Intended-path solver: recursive listing narrowed by a targeted Select-String."""

import urllib.parse

import paramiko

from openrange.content.solver import SolveResult, TaskResult, find_flags

SEARCH = (
    "Get-ChildItem -File -Recurse $HOME/winfs | "
    "Select-String -CaseSensitive -Pattern 'FLAG\\{' | "
    "Select-Object -First 1 -ExpandProperty Line"
)


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
        _, stdout, stderr = client.exec_command(SEARCH, timeout=40)
        out = stdout.read().decode(errors="replace")
        err = stderr.read().decode(errors="replace")
    finally:
        client.close()
    flags = find_flags(out)
    captured = flags[0] if flags else None
    return SolveResult(
        results=[
            TaskResult(
                task_id="pwsh-hunt",
                ok=bool(captured),
                captured=captured,
                detail=None if captured else f"no flag from pwsh search: {out[:200]} {err[:200]}",
            )
        ]
    )
