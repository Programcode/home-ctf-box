"""Intended-path solver: peel the four encoding layers and recover the flag."""

import base64
import codecs

import httpx

from openrange.content.solver import SolveResult, TaskResult, find_flags


def solve(ctx) -> SolveResult:  # type: ignore[no-untyped-def]
    expected = ctx.expected_flags["peel-the-layers"]
    with httpx.Client(base_url=ctx.url(), timeout=10) as client:
        blob = client.get("/api/archive").json()["blob"]

        # Layer 4: base64. Layer 3: hex.
        hex_text = base64.b64decode(blob).decode()
        layer_b64 = bytes.fromhex(hex_text).decode()

        # Layer 2: base64. Layer 1: rot13.
        rot13_text = base64.b64decode(layer_b64).decode()
        plaintext = codecs.decode(rot13_text, "rot13")

        # Guided flow also exercises the digest identifier once.
        verdict = client.post(
            "/api/identify",
            json={"digest": "d34db33f" * 8},
        ).json()

    captured = find_flags(plaintext)
    captured = captured[0] if captured else None
    ok = (
        captured == expected
        and verdict.get("algorithm") == "SHA-256"
        and verdict.get("bits") == 256
    )
    detail = None if ok else f"decoded={plaintext!r} identify={verdict}"
    return SolveResult(
        results=[TaskResult(task_id="peel-the-layers", ok=ok, captured=captured, detail=detail)]
    )
