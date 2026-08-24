"""Intended-path solver: recover reused DSA k, then x, then forge an admin token."""

import hashlib

import httpx

from openrange.content.solver import SolveResult, TaskResult, find_flags


def hash_message(message: str, q_bits: int = 160) -> int:
    return int.from_bytes(hashlib.sha256(message.encode()).digest(), "big") >> (256 - q_bits)


def solve(ctx) -> SolveResult:  # type: ignore[no-untyped-def]
    expected = ctx.expected_flags["forge-admin-token"]
    client = httpx.Client(base_url=ctx.url(), timeout=10)
    audit = client.get("/api/audit").json()

    p = int(audit["params"]["p"])
    q = int(audit["params"]["q"])
    g = int(audit["params"]["g"])
    y = int(audit["params"]["y"])

    (m1, r1, s1), (m2, r2, s2) = [
        (e["message"], int(e["r"]), int(e["s"])) for e in audit["entries"]
    ]
    assert r1 == r2, "the telltale: identical r means identical nonce"

    # Same-nonce recovery. From s = k^-1 (z + x r):
    #   s1 - s2 = k^-1 (z1 - z2)  =>  k = (z1 - z2) / (s1 - s2)
    z1 = hash_message(m1)
    z2 = hash_message(m2)
    k = (z1 - z2) * pow(s1 - s2, -1, q) % q
    assert pow(g, k, p) % q == r1, "recovered nonce fails the r check"

    # Private key: x = (s1 k - z1) / r1
    x = (s1 * k - z1) * pow(r1, -1, q) % q
    assert pow(g, x, p) == y, "recovered private key does not match public y"

    # Forge a fresh signature over our own admin token.
    token = "grant-ledgerline-admin"
    k_fresh = (k + 1) % q or 1
    z_t = hash_message(token)
    r_new = pow(g, k_fresh, p) % q
    s_new = pow(k_fresh, -1, q) * (z_t + x * r_new) % q

    resp = client.post("/admin/token", data={"token": token, "r": str(r_new), "s": str(s_new)})
    client.close()
    flags = find_flags(resp.text)
    captured = flags[0] if flags else None
    ok = captured == expected and token in resp.text
    detail = None if ok else f"status={resp.status_code} recovered_x={x}"
    return SolveResult(
        results=[TaskResult(task_id="forge-admin-token", ok=ok, captured=captured, detail=detail)]
    )
