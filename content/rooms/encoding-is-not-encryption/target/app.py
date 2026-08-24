"""Meridian Archive training desk: encoding layers and hash shapes. Room target only."""

import base64
import codecs
import hashlib
import os

from flask import Flask, jsonify, request

app = Flask(__name__)
FLAG = os.environ["ROOM_FLAG"]

KNOWN_DIGESTS = [
    {
        "label": "sample-a",
        "digest": hashlib.md5(b"meridian-archive-sample").hexdigest(),
    },
    {
        "label": "sample-b",
        "digest": hashlib.sha1(b"meridian-archive-sample").hexdigest(),
    },
    {
        "label": "sample-c",
        "digest": hashlib.sha256(b"meridian-archive-sample").hexdigest(),
    },
]

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Meridian Archive Training Desk</title>
<style>
body { background:#F7F6F3; font-family:Helvetica,Arial,sans-serif; display:flex; justify-content:center; padding-top:8vh; }
.box { background:#fff; border:1px solid #EAEAEA; border-radius:8px; padding:2rem; width:40rem; margin:.6rem; }
code, pre { background:#F7F6F3; border-radius:6px; padding:.15rem .4rem; font-size:.85rem; overflow-wrap:anywhere; }
h1 { letter-spacing:-0.02em; font-size:1.35rem; }
p, li { color:#787774; font-size:.9rem; }
table { border-collapse:collapse; width:100%; font-size:.85rem; }
td { border-top:1px solid #EAEAEA; padding:.35rem .3rem; }
input { width:100%%; padding:.45rem; border:1px solid #EAEAEA; border-radius:6px; }
button { background:#111; color:#fff; border:none; border-radius:6px; padding:.5rem 1rem; cursor:pointer; }
.result { background:#EDF3EC; color:#346538; border-radius:6px; padding:.5rem .75rem; }
</style></head><body>%s</body></html>"""


def build_chain(secret: str) -> tuple[str, list[dict]]:
    """Apply four reversible layers, outermost applied last."""
    layer_rot13 = codecs.encode(secret, "rot13")
    layer_b64 = base64.b64encode(layer_rot13.encode()).decode()
    layer_hex = layer_b64.encode().hex()
    sealed = base64.b64encode(layer_hex.encode()).decode()
    manifest = [
        {"order": 1, "name": "rot13", "note": "letters shifted 13 places"},
        {"order": 2, "name": "base64", "note": "A-Za-z0-9+/ alphabet with = padding"},
        {"order": 3, "name": "hex", "note": "lowercase 0-9a-f, two chars per byte"},
        {"order": 4, "name": "base64", "note": "applied last, peel first"},
    ]
    return sealed, manifest


SEALED, MANIFEST = build_chain(FLAG)


def identify(digest: str) -> dict:
    clean = digest.strip().lower()
    hex_ok = all(c in "0123456789abcdef" for c in clean) and len(clean) % 2 == 0
    if not hex_ok or len(clean) == 0:
        return {"algorithm": "unknown", "bits": None}
    bits = len(clean) * 4
    names = {128: "MD5", 160: "SHA-1", 256: "SHA-256"}
    return {"algorithm": names.get(bits, "unknown"), "bits": bits}


@app.get("/healthz")
def healthz():
    return "ok"


@app.get("/")
def home():
    rows = "".join(
        f"<tr><td>{d['label']}</td><td><code>{d['digest']}</code></td></tr>" for d in KNOWN_DIGESTS
    )
    return PAGE % (
        """
<div class="box">
<h1>Meridian Archive Training Desk</h1>
<p>New archivists keep wrapping records in transfer formats until nobody
can read them, then call the result "encrypted". This desk teaches the
difference. The sealed blob below is the same secret dressed in four
reversible layers.</p>
<p>Sealed blob: <code>"""
        + SEALED
        + """</code></p>
<p>The API at <code>/api/archive</code> serves the blob plus its layer
manifest as JSON. Peel it down to plaintext.</p>
</div>
<div class="box">
<h1>Digest identification lab</h1>
<p>Hashes are one-way fingerprints, not containers. You can still tell
formats apart by shape:</p>
<table><tr><td>MD5</td><td>32 hex chars (128 bits)</td></tr>
<tr><td>SHA-1</td><td>40 hex chars (160 bits)</td></tr>
<tr><td>SHA-256</td><td>64 hex chars (256 bits)</td></tr></table>
<p>Samples:</p>
<table>"""
        + rows
        + """</table>
<form method="post" action="/identify">
<input name="digest" placeholder="paste any digest">
<button type="submit">Identify</button>
</form>
</div>"""
    )


@app.post("/identify")
def identify_form():
    verdict = identify(request.form.get("digest", ""))
    return PAGE % (
        f"""<div class='box'><h1>Digest identification lab</h1>
<p class='result'>algorithm: {verdict["algorithm"]}, bits: {verdict["bits"]}</p>
<p><a href="/">back to the desk</a></p></div>"""
    )


@app.get("/api/archive")
def archive():
    return jsonify({"blob": SEALED, "layers": MANIFEST})


@app.post("/api/identify")
def identify_api():
    data = request.get_json(silent=True) or {}
    return jsonify(identify(str(data.get("digest", ""))))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
