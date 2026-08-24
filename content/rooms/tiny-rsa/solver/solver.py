"""Intended-path solver: integer cube roots over each sealed block."""

import httpx

from openrange.content.solver import SolveResult, TaskResult, find_flags

CHUNK = 16


def icbrt(x: int) -> int:
    """Integer cube root by binary search, pure python ints."""
    if x < 0:
        raise ValueError("negative input")
    lo, hi = 0, 1 << (x.bit_length() // 3 + 2)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if mid**3 <= x:
            lo = mid
        else:
            hi = mid - 1
    return lo


def solve(ctx) -> SolveResult:  # type: ignore[no-untyped-def]
    expected = ctx.expected_flags["cube-root-the-blocks"]
    with httpx.Client(base_url=ctx.url(), timeout=10) as client:
        key = client.get("/api/pubkey").json()
        sealed = client.get("/api/sealed").json()

    n = int(key["n"])
    e = int(key["e"])
    assert e == 3 and n.bit_length() == 512

    pieces = []
    for block_hex in sealed["blocks"]:
        c = int(block_hex, 16)
        root = icbrt(c)
        # No wraparound happened iff the cube is exact: c = m^3 exactly.
        assert root**3 == c, "ciphertext wrapped the modulus; cube-root path invalid"
        piece = root.to_bytes(CHUNK, "big").lstrip(b"\x00")
        pieces.append(piece)

    plaintext = b"".join(pieces).decode("ascii", "replace")

    flags = find_flags(plaintext)
    captured = flags[0] if flags else None
    ok = captured == expected
    detail = None if ok else f"recovered={plaintext!r}"
    return SolveResult(
        results=[
            TaskResult(task_id="cube-root-the-blocks", ok=ok, captured=captured, detail=detail)
        ]
    )
