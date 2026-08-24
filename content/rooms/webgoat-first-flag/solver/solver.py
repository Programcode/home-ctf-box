"""Intended-path solver for webgoat-first-flag.

Drives the real WebGoat instance: registers a fresh learner account through
the registration endpoint (which signs the account in), then completes the
HTTP Basics assignment through its own attack endpoint and checks the
wire-level completion marker.
"""

import json
import random
import string

import httpx
from openrange.content.solver import SolveResult, TaskResult

ANSWER = "lessonCompleted: true"


def solve(ctx) -> SolveResult:
    user = "hermes" + "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
    task = TaskResult(task_id="http-basics-done", ok=False)
    with httpx.Client(base_url=ctx.url(), timeout=30.0, follow_redirects=True) as client:
        client.get("/WebGoat/registration")
        client.post(
            "/WebGoat/register.mvc",
            data={
                "username": user,
                "password": "Goat12345",
                "matchingPassword": "Goat12345",
                "agree": "agree",
            },
        )
        response = client.post("/WebGoat/HttpBasics/attack1", data={"person": user})
        completed = False
        try:
            payload = response.json()
            completed = bool(payload.get("lessonCompleted"))
        except json.JSONDecodeError:
            completed = '"lessonCompleted" : true' in response.text
        if completed:
            task.ok = True
            task.captured = ANSWER
        else:
            task.detail = f"assignment status {response.status_code}"
    return SolveResult(results=[task])
