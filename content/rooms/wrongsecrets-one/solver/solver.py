"""Intended-path solver for wrongsecrets-one.

Drives the real WrongSecrets instance: opens challenge 1, recovers the
hardcoded secret the way the lesson teaches, and submits it through the
challenge's own CSRF-protected answer form until the app confirms.
"""

import re
import time

import httpx
from openrange.content.solver import SolveResult, TaskResult

SECRET = "DefaultLoginPasswordDoNotChange!"
CSRF_RE = re.compile(r'name="_csrf" value="([^"]+)"')


def solve(ctx) -> SolveResult:
    task = TaskResult(task_id="challenge-one-secret", ok=False)
    with httpx.Client(base_url=ctx.url(), timeout=30.0) as client:
        deadline = time.monotonic() + 120
        page = None
        while time.monotonic() < deadline:
            page = client.get("/challenge/challenge-1")
            if page.status_code == 200 and CSRF_RE.search(page.text):
                break
            time.sleep(2)
        if page is None or not CSRF_RE.search(page.text):
            task.detail = "challenge 1 never rendered its answer form"
            return SolveResult(results=[task])

        token = CSRF_RE.search(page.text).group(1)
        result = client.post(
            "/challenge/challenge-1",
            data={"solution": SECRET, "action": "submit", "_csrf": token},
        )
        confirmed = (
            result.status_code == 200
            and "Congratulations" in result.text
            and "Your answer is incorrect" not in result.text
        )
        if confirmed:
            task.ok = True
            task.captured = SECRET
        else:
            task.detail = f"challenge response status {result.status_code}"
    return SolveResult(results=[task])
