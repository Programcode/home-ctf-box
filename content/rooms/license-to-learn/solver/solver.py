"""Intended-path solver: fill the gdb template, read the expected code, feed it back."""

import re
import urllib.parse

import paramiko

from openrange.content.solver import SolveResult, TaskResult, find_flags

COPY_CMD = "cp /opt/challenges/activator /tmp/activator-copy && chmod 755 /tmp/activator-copy"
NM_CMD = "nm /tmp/activator-copy"
SHEET_CMD = (
    "sed -e 's/@@BREAKPOINT@@/{bp}/' -e 's/@@ARGUMENT@@/1/' "
    "-e 's/@@VARIABLE@@/{var}/' /opt/challenges/cheatsheet.gdb > /tmp/sheet.gdb"
)
GDB_CMD = "gdb -batch -x /tmp/sheet.gdb /tmp/activator-copy"
ACTIVATE_CMD = "/opt/challenges/activator {code}"

SYMBOL_LINE = re.compile(r"^[0-9a-f]+ [A-Za-z] (\S+)$", re.MULTILINE)
MEM_DUMP = re.compile(r":\s+0x([0-9a-f]{8})")


def _target(ctx) -> tuple[str, int]:  # type: ignore[no-untyped-def]
    parsed = urllib.parse.urlsplit(ctx.url("target"))
    return parsed.hostname or "target", parsed.port or 22


def _run(client, cmd: str, timeout: int) -> str:
    _, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    return f"{out}\n{err}"


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
        _run(client, COPY_CMD, 15)
        symbols = _run(client, NM_CMD, 20)

        names = set(SYMBOL_LINE.findall(symbols))
        report_fn = next((n for n in names if n.startswith("report")), None)
        expected_var = next((n for n in names if n.startswith("expected")), None)
        if not report_fn or not expected_var:
            detail = f"needed symbols not found in nm output: {sorted(names)[:10]}"
        else:
            _run(client, SHEET_CMD.format(bp=report_fn, var=expected_var), 15)
            gdb_out = _run(client, GDB_CMD, 90)
            dump = MEM_DUMP.search(gdb_out)
            if dump is None:
                detail = f"gdb produced no memory dump: {gdb_out[-300:]}"
            else:
                code = int(dump.group(1), 16)
                run_out = _run(client, ACTIVATE_CMD.format(code=code), 30)
                flags = find_flags(run_out)
                captured = flags[0] if flags else None
                if not captured:
                    detail = f"expected code {code} from memory did not activate: {run_out[:200]}"
    finally:
        client.close()
    return SolveResult(
        results=[
            TaskResult(
                task_id="debugger-read",
                ok=bool(captured),
                captured=captured,
                detail=detail,
            )
        ]
    )
