"""Intended-path solver: fetch the pcap, recover the FTP password, report."""

import urllib.parse

import httpx

from openrange.content.solver import SolveResult, TaskResult, find_flags


def solve(ctx) -> SolveResult:  # type: ignore[no-untyped-def]
    base = ctx.url()
    pcap = httpx.get(f"{base}/evidence/capture.pcap", timeout=10).content

    marker = pcap.find(b"PASS ")
    if marker == -1:
        return SolveResult(
            results=[
                TaskResult(
                    task_id="recover-the-password",
                    ok=False,
                    detail="no 'PASS ' line found in capture bytes",
                )
            ]
        )
    end = pcap.find(b"\r\n", marker)
    password = pcap[marker + len(b"PASS ") : end].decode(errors="replace")

    res = httpx.get(
        f"{base}/report",
        params={"password": urllib.parse.quote(password)},
        timeout=10,
    )
    flags = find_flags(res.text)
    captured = flags[0] if flags else None
    return SolveResult(
        results=[
            TaskResult(
                task_id="recover-the-password",
                ok=bool(captured),
                captured=captured,
                detail=None if captured else "report endpoint did not yield a flag",
            )
        ]
    )
