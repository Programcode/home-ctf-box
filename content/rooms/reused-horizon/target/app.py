"""Horizon Sync telemetry gateway: one XOR key protects every frame. Room target only."""

import hashlib
import os

from flask import Flask, jsonify

app = Flask(__name__)
FLAG = os.environ["ROOM_FLAG"]

KEY = hashlib.sha256(b"horizon-sync|" + FLAG.encode()).digest()  # 32 bytes
KNOWN_HEADER = b"HORIZON-SYNC-V1::TELEMETRY::FRAME-HEADER-BLOCK0000"[:48]
assert len(KNOWN_HEADER) >= len(FLAG.encode()) and len(KNOWN_HEADER) % 8 == 0


def xor_repeat(data: bytes, key: bytes) -> bytes:
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))


SECRET_FRAME = xor_repeat(FLAG.encode(), KEY)
HEADER_FRAME = xor_repeat(KNOWN_HEADER, KEY)

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Horizon Sync Gateway</title>
<style>
body { background:#F7F6F3; font-family:Helvetica,Arial,sans-serif; display:flex; justify-content:center; padding-top:8vh; }
.box { background:#fff; border:1px solid #EAEAEA; border-radius:8px; padding:2rem; width:40rem; }
code, pre { background:#F7F6F3; border-radius:6px; padding:.15rem .4rem; font-size:.85rem; overflow-wrap:anywhere; }
h1 { letter-spacing:-0.02em; font-size:1.35rem; }
p, li { color:#787774; font-size:.9rem; }
</style></head><body>
<div class="box">
<h1>Horizon Sync Telemetry Gateway</h1>
<p>Every frame this gateway emits is protected with a fast XOR layer so
field links stay cheap. One 32-byte session key covers all traffic,
repeated as needed. The frame header is fixed by the wire protocol
section 4.2, so it is the same on every install.</p>
<p>Fixed header (plaintext, protocol constant):<br>
<code>%s</code></p>
<p>Header frame (hex): <code>%s</code></p>
<p>Secret payload frame (hex): <code>%s</code></p>
<p>Machine-readable copies live at <code>/api/frame</code>.</p>
</div>
</body></html>""" % (
    KNOWN_HEADER.decode(),
    HEADER_FRAME.hex(),
    SECRET_FRAME.hex(),
)


@app.get("/healthz")
def healthz():
    return "ok"


@app.get("/")
def home():
    return PAGE


@app.get("/api/frame")
def frame():
    return jsonify(
        {
            "secret_hex": SECRET_FRAME.hex(),
            "header_hex": HEADER_FRAME.hex(),
            "known_header": KNOWN_HEADER.decode(),
            "cipher": "xor repeating 32-byte session key",
        }
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
