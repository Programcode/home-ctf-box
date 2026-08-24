"""Intended-path solver for juice-shop-tour.

Drives the real OWASP Juice Shop instance: confirms the storefront serves,
finds the hidden score-board route the way the lesson teaches (route
string inside the served JavaScript bundle), then opens that route.
"""

import httpx
from openrange.content.solver import SolveContext, SolveResult, TaskResult

ANSWER = "/score-board"


def solve(ctx: SolveContext) -> SolveResult:
    with httpx.Client(base_url=ctx.url(), timeout=20.0, follow_redirects=True) as client:
        root = client.get("/")
        bundle = client.get("/main.js")
        board = client.get(ANSWER)
        route_in_bundle = ANSWER in bundle.text
        found = root.status_code == 200 and board.status_code == 200 and route_in_bundle
        return SolveResult(
            results=[
                TaskResult(
                    task_id="find-score-board",
                    ok=found,
                    captured=ANSWER if found else None,
                    detail=(
                        f"GET / -> {root.status_code}, route {ANSWER!r} in main.js: "
                        f"{route_in_bundle}, GET {ANSWER} -> {board.status_code}"
                    ),
                )
            ]
        )
