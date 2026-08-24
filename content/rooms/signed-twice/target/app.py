"""LedgerLine audit signer: DSA over small documented fields, k reused twice. Room target only."""

import hashlib
import os
import random

from flask import Flask, jsonify, request

app = Flask(__name__)
FLAG = os.environ["ROOM_FLAG"]

Q_BITS = 160
P_BITS = 512


def is_probable_prime(n: int, rounds: int = 40) -> bool:
    if n < 2:
        return False
    for p in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37):
        if n % p == 0:
            return n == p
    d = n - 1
    r = 0
    while d % 2 == 0:
        d //= 2
        r += 1
    rng = random.Random(n)
    for _ in range(rounds):
        a = rng.randrange(2, n - 1)
        x = pow(a, d, n)
        if x in (1, n - 1):
            continue
        for _ in range(r - 1):
            x = pow(x, 2, n)
            if x == n - 1:
                break
        else:
            return False
    return True


def generate_params(flag: str):
    """Deterministic safe-ish DSA domain parameters, sizes documented."""
    seed = int.from_bytes(hashlib.sha256(b"signed-twice|" + flag.encode()).digest(), "big")
    rng = random.Random(seed)

    while True:
        q = rng.getrandbits(Q_BITS) | (1 << (Q_BITS - 1)) | 1
        if is_probable_prime(q):
            break
    while True:
        k = rng.getrandbits(P_BITS - Q_BITS) | (1 << (P_BITS - Q_BITS - 1))
        p = q * k + 1
        if p.bit_length() == P_BITS and is_probable_prime(p):
            break
    g = 2
    while pow(g, (p - 1) // q, p) == 1:
        g += 1
    g = pow(g, (p - 1) // q, p)
    x = rng.randrange(1, q)
    y = pow(g, x, p)
    return p, q, g, x, y


def hash_message(message: bytes) -> int:
    """Leftmost 160 bits of SHA-256, per the posted spec."""
    return int.from_bytes(hashlib.sha256(message).digest(), "big") >> 96


def sign(message: str, k: int) -> tuple[int, int]:
    z = hash_message(message.encode())
    r = pow(G, k, P) % Q
    s = pow(k, -1, Q) * (z + X * r) % Q
    if r == 0 or s == 0:  # pragma: no cover - probability ~2^-159
        raise RuntimeError("degenerate signature")
    return r, s


P, Q, G, X, Y = generate_params(FLAG)

ENTRY_MESSAGES = [
    "ledger-entry-0001:intake",
    "ledger-entry-0002:release",
]

# The batch signer draws one nonce and forgets to advance it, so both
# entries carry signatures made with the same k. Deterministic choice.
K_REUSED = int.from_bytes(hashlib.sha256(b"k|" + FLAG.encode()).digest(), "big") % Q or 1
SIGNATURES = [sign(m, K_REUSED) for m in ENTRY_MESSAGES]

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>LedgerLine Audit Signer</title>
<style>
body { background:#F7F6F3; font-family:Helvetica,Arial,sans-serif; display:flex; justify-content:center; padding-top:8vh; }
.box { background:#fff; border:1px solid #EAEAEA; border-radius:8px; padding:2rem; width:42rem; margin-bottom:.6rem; }
code, pre { background:#F7F6F3; border-radius:6px; padding:.15rem .4rem; font-size:.82rem; overflow-wrap:anywhere; }
h1 { letter-spacing:-0.02em; font-size:1.35rem; }
p, li { color:#787774; font-size:.9rem; }
input { width:100%%; padding:.45rem; border:1px solid #EAEAEA; border-radius:6px; }
button { background:#111; color:#fff; border:none; border-radius:6px; padding:.5rem 1rem; cursor:pointer; }
</style></head><body>
<div class="box">
<h1>LedgerLine Audit Signer</h1>
<p>The svc-admin batch signer approves ledger entries with DSA over our
documented toy fields: 512-bit p, 160-bit q, SHA-256 truncated to its
leftmost 160 bits. Domain parameters and today's signature records are
published at <code>/api/audit</code> for transparency.</p>
<p>Admin tokens are accepted at <code>POST /admin/token</code> with form
fields <code>token</code>, <code>r</code>, <code>s</code> (decimal).
A valid svc-admin signature over your token string unlocks the desk.</p>
</div>
<div class="box">
<h1>Token desk</h1>
<form method="post" action="/admin/token">
<input name="token" placeholder="token string">
<input name="r" placeholder="r">
<input name="s" placeholder="s">
<button type="submit">Submit</button>
</form>
</div>
</body></html>"""


@app.get("/healthz")
def healthz():
    return "ok"


@app.get("/")
def home():
    return PAGE


@app.get("/api/audit")
def audit():
    return jsonify(
        {
            "params": {"p": str(P), "q": str(Q), "g": str(G), "y": str(Y)},
            "signer": "svc-admin",
            "hash_spec": "sha256 leftmost 160 bits: z = int(sha256(m)) >> 96",
            "entries": [
                {
                    "message": m,
                    "r": str(SIGNATURES[i][0]),
                    "s": str(SIGNATURES[i][1]),
                }
                for i, m in enumerate(ENTRY_MESSAGES)
            ],
        }
    )


def verify(message: str, r: int, s: int) -> bool:
    if not (0 < r < Q and 0 < s < Q):
        return False
    z = hash_message(message.encode())
    w = pow(s, -1, Q)
    u1 = z * w % Q
    u2 = r * w % Q
    v = (pow(G, u1, P) * pow(Y, u2, P) % P) % Q
    return v == r


@app.post("/admin/token")
def admin_token():
    token = request.form.get("token", "")
    try:
        r = int(request.form.get("r", ""))
        s = int(request.form.get("s", ""))
    except ValueError:
        return PAGE.replace("<h1>Token desk</h1>", "<h1>Token desk (bad numbers)</h1>"), 400
    if verify(token, r, s):
        granted = (
            f"<h1>Token desk</h1>"
            f"<p style='color:#346538'>Signature verified for token "
            f"<code>{token}</code>. Admin session granted.</p>"
            f"<p><code>{FLAG}</code></p>"
        )
        return PAGE.replace("<h1>Token desk</h1>", granted)
    return PAGE.replace("<h1>Token desk</h1>", "<h1>Token desk (signature rejected)</h1>"), 403


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, threaded=True)
