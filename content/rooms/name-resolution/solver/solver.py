"""Intended-path solver: query the claimed name, lift the blob, submit it."""

import re
import time
import urllib.parse

import httpx
import paramiko

from openrange.content.solver import SolveResult, TaskResult, find_flags

BLOB_RE = re.compile(r"SIM-HASH-[0-9a-f]{32}")
QUERY_CMD = "python3 /home/learner/tools/namesim_query.py --proto llmnr --name FILESRV01"
CAPTURE_LOG = "cat /srv/public/responder-capture.log"


def _target(ctx) -> tuple[str, int]:  # type: ignore[no-untyped-def]
    parsed = urllib.parse.urlsplit(ctx.url("target"))
    return parsed.hostname or "target", 22


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


def _run(client: paramiko.SSHClient, cmd: str, timeout: int = 20) -> tuple[str, str]:
    _, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    return stdout.read().decode(errors="replace"), stderr.read().decode(errors="replace")


def solve(ctx) -> SolveResult:  # type: ignore[no-untyped-def]
    host, port = _target(ctx)

    client = _connect(host, port)
    try:
        # The responder-sim starts at boot; a short settle delay keeps the
        # first query from racing its UDP bind.
        time.sleep(1.0)
        reply, reply_err = _run(client, QUERY_CMD)
        match = BLOB_RE.search(reply) or BLOB_RE.search(reply_err)
        if not match:
            log_out, _log_err = _run(client, CAPTURE_LOG)
            match = BLOB_RE.search(log_out)
    finally:
        client.close()

    if not match:
        return SolveResult(
            results=[
                TaskResult(
                    task_id="capture-and-submit",
                    ok=False,
                    detail=f"no SIM-HASH captured; client said: {reply[:160]} {reply_err[:120]}",
                )
            ]
        )

    blob = match.group(0)
    res = httpx.post(f"{ctx.url('target')}/submit", data={"capture": blob}, timeout=10)
    flags = find_flags(res.text)
    captured = flags[0] if flags else None
    detail = None if captured else f"checker rejected blob {blob}: {res.text[:160]}"
    return SolveResult(
        results=[
            TaskResult(
                task_id="capture-and-submit", ok=bool(captured), captured=captured, detail=detail
            )
        ]
    )
