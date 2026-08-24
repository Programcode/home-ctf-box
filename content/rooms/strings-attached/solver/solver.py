"""Intended-path solver: triage ledger with strings, then decode its xor export."""

import re
import urllib.parse

import paramiko

from openrange.content.solver import SolveResult, TaskResult, find_flags

STRINGS_CMD = "strings /opt/challenges/ledger"
EXPORT_CMD = "/opt/challenges/ledger --export-secrets"
KEY_RE = re.compile(r"export-key=0x([0-9A-Fa-f]{2})")


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
        _, strings_out, _ = client.exec_command(STRINGS_CMD, timeout=30)
        listing = strings_out.read().decode(errors="replace")
        _, export_out, export_err = client.exec_command(EXPORT_CMD, timeout=20)
        exported = export_out.read().decode(errors="replace")
        err = export_err.read().decode(errors="replace")

        captured = None
        detail = None
        if "--export-secrets" not in listing:
            detail = f"strings output lacks the hidden mode: {listing[:200]}"
        else:
            key_match = KEY_RE.search(exported)
            blob_line = next(
                (ln for ln in exported.splitlines() if ln.startswith("secret-blob:")),
                "",
            )
            if key_match is None or not blob_line:
                detail = f"no key or blob in export output: {exported[:200]} {err[:200]}"
            else:
                key = int(key_match.group(1), 16)
                blob = bytes.fromhex(blob_line.split(":", 1)[1].replace(" ", ""))
                plain = bytes(b ^ key for b in blob).decode("ascii", errors="replace")
                flags = find_flags(plain)
                captured = flags[0] if flags else None
                if not captured:
                    detail = f"decoded blob held no flag: {plain[:120]}"
    finally:
        client.close()
    return SolveResult(
        results=[
            TaskResult(
                task_id="export-secrets",
                ok=bool(captured),
                captured=captured,
                detail=detail,
            )
        ]
    )
