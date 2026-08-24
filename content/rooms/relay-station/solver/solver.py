"""Intended-path solver: run the room's relay-sim client and capture the flag."""

import subprocess
import sys
import tempfile
from pathlib import Path

import httpx

from openrange.content.solver import SolveResult, TaskResult, find_flags


def solve(ctx) -> SolveResult:  # type: ignore[no-untyped-def]
    base = ctx.url("target")

    # Sanity: the coordinator must be up and deterministic before relaying.
    first = httpx.get(
        f"{base}/coordinator/challenge", params={"target": "fileserver"}, timeout=10
    ).json()
    second = httpx.get(
        f"{base}/coordinator/challenge", params={"target": "fileserver"}, timeout=10
    ).json()
    if first.get("challenge") != second.get("challenge"):
        return SolveResult(
            results=[
                TaskResult(
                    task_id="relay-the-printer",
                    ok=False,
                    detail="coordinator challenges are not deterministic",
                )
            ]
        )

    with tempfile.TemporaryDirectory() as tmp:
        script_path = Path(tmp) / "relay-sim.py"
        script = httpx.get(f"{base}/tools/relay-sim.py", timeout=10).text
        script_path.write_text(script)

        # Intended path runs the room-provided stdlib client.
        proc = subprocess.run(  # noqa: S603
            [sys.executable, str(script_path), "--base", base],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if proc.returncode != 0:
            return SolveResult(
                results=[
                    TaskResult(
                        task_id="relay-the-printer",
                        ok=False,
                        detail=f"relay-sim.py failed: {proc.stderr[:200]}",
                    )
                ]
            )

    flags = find_flags(proc.stdout)
    captured = flags[0] if flags else None
    detail = None
    if not captured:
        detail = f"relay did not yield a flag; stdout tail: {proc.stdout[-200:]}"
    return SolveResult(
        results=[
            TaskResult(
                task_id="relay-the-printer",
                ok=bool(captured),
                captured=captured,
                detail=detail,
            )
        ]
    )
