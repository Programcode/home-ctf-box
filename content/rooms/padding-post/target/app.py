"""Postmaster delivery API: CBC padding oracle by design. Room target only."""

import hashlib
import os

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from flask import Flask, jsonify, request

app = Flask(__name__)
FLAG = os.environ["ROOM_FLAG"]

KEY = hashlib.sha256(b"padding-post|" + FLAG.encode()).digest()  # AES-256
IV = hashlib.sha256(b"padding-post|iv|" + FLAG.encode()).digest()[:16]  # fixed per session
BANNER = b"PADDINGPOST-V1::"


def pkcs7_pad(data: bytes, block: int = 16) -> bytes:
    n = block - (len(data) % block)
    return data + bytes([n]) * n


def aes_decrypt_raw(data: bytes) -> bytes:
    dec = Cipher(algorithms.AES(KEY), modes.CBC(IV)).decryptor()
    return dec.update(data) + dec.finalize()


def aes_encrypt_raw(data: bytes) -> bytes:
    enc = Cipher(algorithms.AES(KEY), modes.CBC(IV)).encryptor()
    return enc.update(data) + enc.finalize()


PLAINTEXT = BANNER + pkcs7_pad(FLAG.encode())
SEALED_CT = aes_encrypt_raw(PLAINTEXT)

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Postmaster Delivery API</title>
<style>
body { background:#F7F6F3; font-family:Helvetica,Arial,sans-serif; display:flex; justify-content:center; padding-top:8vh; }
.box { background:#fff; border:1px solid #EAEAEA; border-radius:8px; padding:2rem; width:40rem; }
code, pre { background:#F7F6F3; border-radius:6px; padding:.15rem .4rem; font-size:.85rem; overflow-wrap:anywhere; }
h1 { letter-spacing:-0.02em; font-size:1.35rem; }
p, li { color:#787774; font-size:.9rem; }
</style></head><body>
<div class="box">
<h1>Postmaster Delivery API</h1>
<p>Envelopes travel as AES-CBC ciphertext under a session key this
service never shows anyone. The integrity desk only answers one
question about a submitted envelope: did the padding check out? The
desk is fast and never gets tired, so ask it as often as you like.</p>
<p>Envelope endpoint: <code>GET /api/message</code></p>
<p>Integrity desk: <code>POST /api/decrypt</code> with JSON
<code>{"ct": "&lt;hex&gt;"}</code>, answered as
<code>{"valid_padding": true|false}</code>.</p>
<p>Scheme notes: AES-256-CBC, PKCS#7 padding, fixed IV for the whole
session, plaintext starts with the 16-byte banner
<code>PADDINGPOST-V1::</code>.</p>
</div>
</body></html>"""


@app.get("/healthz")
def healthz():
    return "ok"


@app.get("/")
def home():
    return PAGE


@app.get("/api/message")
def message():
    return jsonify(
        {
            "iv_hex": IV.hex(),
            "ct_hex": SEALED_CT.hex(),
            "scheme": "AES-256-CBC PKCS#7, fixed session IV",
            "banner_hint": "plaintext begins with a known 16-byte banner block",
        }
    )


@app.post("/api/decrypt")
def decrypt():
    """The oracle. Answers one boolean and nothing else.

    Deliberately not rate limited: the pedagogy of this room is that an
    adaptive attacker needs thousands of queries, so learners can watch
    the side channel work. The service holds synthetic data only.
    """
    data = request.get_json(silent=True) or {}
    try:
        ct = bytes.fromhex(str(data.get("ct", "")))
    except ValueError:
        return jsonify({"valid_padding": False})
    if len(ct) < 32 or len(ct) % 16 != 0 or len(ct) > 4096:
        return jsonify({"valid_padding": False})
    pt = aes_decrypt_raw(ct)
    last = pt[-16:]
    pad_len = last[-1]
    ok = 1 <= pad_len <= 16 and last[-pad_len:] == bytes([pad_len]) * pad_len
    return jsonify({"valid_padding": bool(ok)})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, threaded=True)
