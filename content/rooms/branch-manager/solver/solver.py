"""Intended-path solver: derive the license key from notes.asm, then submit it."""

import re
import urllib.parse

import paramiko

from openrange.content.solver import SolveResult, TaskResult, find_flags

NOTES_CMD = "cat /opt/challenges/notes.asm"
CHECK_CMD = "printf '%s\\n' '{key}' | /opt/challenges/license-check"
VERIFY_SLICE = re.compile(r"<verify_key>:\n(.*?)\n\n", re.DOTALL)
CMP_IMM = re.compile(r"cmp\S*\s+\$0x([0-9a-f]+)")


def _derive_key(constants: list[int]) -> str:
    length, total, first = constants
    if not (0 < first < 128) or length < 1:
        raise ValueError(f"implausible constants from notes.asm: {constants}")
    remaining = total - first
    base, extra = divmod(remaining, length - 1)
    if not (0x20 <= base <= 0x7E) or (base + 1 if extra else base) > 0x7E:
        raise ValueError(f"no printable key fits constants {constants}")
    filler = chr(base) * (length - 1 - extra) + chr(base + 1) * extra
    return chr(first) + filler


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
        _, notes_out, notes_err = client.exec_command(NOTES_CMD, timeout=30)
        notes = notes_out.read().decode(errors="replace")
        err = notes_err.read().decode(errors="replace")

        captured = None
        detail = None
        section = VERIFY_SLICE.search(notes)
        if not section:
            detail = f"verify_key section missing from notes.asm: {err[:200]}"
        else:
            constants = [int(v, 16) for v in CMP_IMM.findall(section.group(1))]
            if len(constants) != 3:
                detail = f"expected 3 cmp immediates in verify_key, saw {constants}"
            else:
                key = _derive_key(constants)
                _, run_out, run_err = client.exec_command(CHECK_CMD.format(key=key), timeout=20)
                granted = run_out.read().decode(errors="replace")
                rerr = run_err.read().decode(errors="replace")
                flags = find_flags(granted)
                captured = flags[0] if flags else None
                if not captured:
                    detail = (
                        f"key {key!r} derived from {constants} did not yield a flag: "
                        f"{granted[:200]} {rerr[:200]}"
                    )
    finally:
        client.close()
    return SolveResult(
        results=[
            TaskResult(
                task_id="craft-license",
                ok=bool(captured),
                captured=captured,
                detail=detail,
            )
        ]
    )
