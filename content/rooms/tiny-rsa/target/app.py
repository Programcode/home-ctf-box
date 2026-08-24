"""FastSign TinyVault: textbook RSA with a small exponent. Room target only."""

import hashlib
import os
import random

from flask import Flask, jsonify

app = Flask(__name__)
FLAG = os.environ["ROOM_FLAG"]

CHUNK = 16  # bytes per sealed block, zero-padded on the left
PUBLIC_EXPONENT = 3


def is_probable_prime(n: int, rounds: int = 40) -> bool:
    if n < 2:
        return False
    small_primes = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37]
    for p in small_primes:
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


def generate_key(flag: str) -> tuple[int, int]:
    """Deterministic per-session 512-bit modulus from the flag material."""
    seed = int.from_bytes(hashlib.sha256(b"tiny-rsa|" + flag.encode()).digest(), "big")
    rng = random.Random(seed)

    def prime(bits: int) -> int:
        while True:
            candidate = rng.getrandbits(bits) | (1 << (bits - 1)) | 1
            if is_probable_prime(candidate):
                return candidate

    while True:
        p = prime(256)
        q = prime(256)
        n = p * q
        # e = 3 must not share a factor with phi for RSA to be well formed.
        if n.bit_length() == 512 and ((p - 1) * (q - 1)) % PUBLIC_EXPONENT != 0:
            return n


N = generate_key(FLAG)


def seal_chunk(chunk: str) -> str:
    raw = chunk.encode().rjust(CHUNK, b"\x00")
    m = int.from_bytes(raw, "big")
    assert m**PUBLIC_EXPONENT < N, "chunk too large for cube-root-free guarantee"
    return format(pow(m, PUBLIC_EXPONENT, N), "x")


SEALED_BLOCKS = [seal_chunk(FLAG[i : i + CHUNK]) for i in range(0, len(FLAG), CHUNK)]

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>FastSign TinyVault</title>
<style>
body { background:#F7F6F3; font-family:Helvetica,Arial,sans-serif; display:flex; justify-content:center; padding-top:8vh; }
.box { background:#fff; border:1px solid #EAEAEA; border-radius:8px; padding:2rem; width:42rem; }
code, pre { background:#F7F6F3; border-radius:6px; padding:.15rem .4rem; font-size:.82rem; overflow-wrap:anywhere; }
h1 { letter-spacing:-0.02em; font-size:1.35rem; }
p, li { color:#787774; font-size:.9rem; }
</style></head><body>
<div class="box">
<h1>FastSign TinyVault Sealing Desk</h1>
<p>Sealing here is instant because the vault uses a slim 512-bit
modulus with public exponent e=3, and messages are split into short
16-byte blocks padded on the left with zero bytes before sealing. No
randomized OAEP, no salt: textbook RSA, the kind you can do by hand.</p>
<p>Modulus n (<code>/api/pubkey</code>):<br><code>%d</code></p>
<p>e = <code>3</code>, chunk size = <code>%d</code> bytes</p>
<p>Sealed payload (<code>/api/sealed</code>):</p>
<pre>%s</pre>
</div>
</body></html>""" % (
    N,
    CHUNK,
    "\n".join(SEALED_BLOCKS),
)


@app.get("/healthz")
def healthz():
    return "ok"


@app.get("/")
def home():
    return PAGE


@app.get("/api/pubkey")
def pubkey():
    return jsonify({"n": str(N), "e": PUBLIC_EXPONENT, "bits": N.bit_length()})


@app.get("/api/sealed")
def sealed():
    return jsonify(
        {
            "scheme": "textbook RSA e=3, 16-byte left-zero-padded chunks, hex blocks",
            "blocks": SEALED_BLOCKS,
        }
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
