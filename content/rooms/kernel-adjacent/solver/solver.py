"""Intended-path solver: facts, triage, precondition edits, checker run."""

import re

import paramiko

from openrange.content.solver import SolveResult, TaskResult, find_flags

FACT_RE = re.compile(r"^FACTS:\s*(\S+)=(.+)$", re.MULTILINE)
BLOCK_RE = re.compile(
    r"=== Candidate [ABC]: (?P<cve>CVE-\d{4}-\d{4,7}) ===\n"
    r"(?P<body>.*?)ELIMINATION BASIS:",
    re.DOTALL,
)
WHEN_KEYS = ("kernel-min", "kernel-max", "userns", "pkexec-present")


def _version_tuple(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split("."))


def _parse_when(body: str) -> dict[str, str]:
    match = re.search(r"APPLIES-WHEN:\s*(.+)", body)
    when: dict[str, str] = {}
    if not match:
        return when
    for token in match.group(1).split():
        key, _, value = token.partition("=")
        if key in WHEN_KEYS:
            when[key] = value
    return when


def _applies(when: dict[str, str], facts: dict[str, str]) -> bool:
    version = _version_tuple(facts.get("kernel-version", "0"))
    low = _version_tuple(when["kernel-min"]) if "kernel-min" in when else None
    high = _version_tuple(when["kernel-max"]) if "kernel-max" in when else None
    if low is not None and (version < low or (high is not None and version > high)):
        return False
    if "userns" in when and when["userns"] != facts.get("userns"):
        return False
    if "pkexec-present" in when:
        expected = "yes" if when["pkexec-present"] == "yes" else "no"
        if expected != facts.get("pkexec-present"):
            return False
    return True


def solve(ctx) -> SolveResult:  # type: ignore[no-untyped-def]
    import urllib.parse

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
        if err.strip():
            out += f"\n[stderr] {err.strip()}"
        return out

    try:
        sysinfo = run("/usr/local/bin/sysinfo")
        facts = {m.group(1): m.group(2) for m in FACT_RE.finditer(sysinfo)}
        if not facts:
            return SolveResult(
                results=[
                    TaskResult(
                        task_id="triage-and-prove",
                        ok=False,
                        detail=f"no FACTS lines from sysinfo: {sysinfo[:200]}",
                    )
                ]
            )
        candidates_txt = run("cat ~/lab/CANDIDATES.txt")

        applicable = []
        for block in BLOCK_RE.finditer(candidates_txt):
            when = _parse_when(block.group("body"))
            if when and _applies(when, facts):
                applicable.append(block.group("cve"))
        if len(applicable) != 1:
            return SolveResult(
                results=[
                    TaskResult(
                        task_id="triage-and-prove",
                        ok=False,
                        detail=f"triage produced {applicable}, expected exactly one",
                    )
                ]
            )
        chosen = applicable[0]

        kernel_line = facts["KERNEL"]
        run("mkdir -p ~/.recon")
        run(f"cat > ~/.recon/kernel.txt <<'EOF'\n{kernel_line}\nEOF")
        conf = (
            f"kernel-version={facts['kernel-version']}\n"
            f"userns={facts['userns']}\n"
            f"pkexec-present={facts['pkexec-present']}\n"
        )
        run(f"cat > ~/lab/preconditions.conf <<'EOF'\n{conf}EOF")

        output = run(f"sudo -n /usr/local/bin/exploit-checker --cve {chosen}", timeout=30)
    finally:
        client.close()

    flags = find_flags(output)
    captured = flags[0] if flags else None
    detail = (
        f"checker accepted {chosen} after recon + conf validation"
        if captured
        else f"checker did not print a flag: {output[-300:]}"
    )
    return SolveResult(
        results=[
            TaskResult(
                task_id="triage-and-prove",
                ok=captured is not None,
                captured=captured,
                detail=detail,
            )
        ]
    )
