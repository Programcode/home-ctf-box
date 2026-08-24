"""Intended-path solver: crib-drag the fixed header to recover the XOR key."""

import httpx

from openrange.content.solver import SolveResult, TaskResult, find_flags


def solve(ctx) -> SolveResult:  # type: ignore[no-untyped-def]
    expected = ctx.expected_flags["recover-frame-flag"]
    with httpx.Client(base_url=ctx.url(), timeout=10) as client:
        data = client.get("/api/frame").json()

    secret = bytes.fromhex(data["secret_hex"])
    header_ct = bytes.fromhex(data["header_hex"])
    known_header = data["known_header"].encode()
    assert len(header_ct) == len(known_header), "crib length mismatch"

    # Keystream recovery: K[i] = C2[i] xor P2[i] wherever the crib covers.
    keystream = bytes(c ^ p for c, p in zip(header_ct, known_header))
    key = keystream[:32]

    # Decrypt the secret frame with the repeating key.
    plain = bytes(b ^ key[i % len(key)] for i, b in enumerate(secret)).decode("ascii", "replace")

    flags = find_flags(plain)
    captured = flags[0] if flags else None
    ok = captured == expected
    detail = None if ok else f"recovered={plain!r}"
    return SolveResult(
        results=[TaskResult(task_id="recover-frame-flag", ok=ok, captured=captured, detail=detail)]
    )
