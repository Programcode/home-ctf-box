"""Fake KDC for the as-rep-arcade room: AS-REP roasting mechanics, simulated.

The cryptography here is deliberately a toy. Real AS-REP encrypted
parts use RC4-HMAC or AES enctypes; this room substitutes XOR against
a keystream derived from sha256(account password). That choice is
disclosed on /kdc/docs, keeps the room deterministic, and removes any
legal gray area: nothing here speaks Kerberos or touches real
credentials.

Plaintext layout of every simulated enc-part:

  bytes 0..15   PREAMBLE (constant, documented verbatim on /kdc/docs)
  bytes 16..    "user=<username>" as UTF-8

The constant prefix lets a wordlist candidate be verified from the
first 16 ciphertext bytes, and the readable tail doubles as a
correctness check after the full decryption.
"""

import base64
import functools
import hashlib
import hmac
import json
import os

from flask import Flask, Response, jsonify, request
from markupsafe import escape

app = Flask(__name__)
FLAG = os.environ["ROOM_FLAG"]

PREAMBLE = b"ASREPSIM-V1\x00\x00\x00\x00\x00"
assert len(PREAMBLE) == 16

# username -> (password, preauth_disabled)
# svc_audit keeps a long random password absent from the published
# wordlist on purpose: leaked material is only a liability when the
# password is weak.
DOMAIN_USERS = {
    "amelia.reyes": ("HarborLight88!", False),
    "marcus.chen": ("WinterOps42", False),
    "svc_archive": ("ArchiveIt92", True),
    "svc_audit": ("zQ7#vRm2!pKd9wXt", True),
}

NOTICE = (
    "Simulation notice: this KDC is a Flask endpoint speaking JSON, not "
    "the Kerberos protocol. Enc-parts are XOR stand-ins with a documented "
    "plaintext layout; no real credentials exist."
)

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>AS-REP Arcade</title>
<style>
body { background:#F7F6F3; font-family:Helvetica,Arial,sans-serif; display:flex; justify-content:center; padding-top:8vh; }
.box { background:#fff; border:1px solid #EAEAEA; border-radius:8px; padding:2.5rem; width:38rem; margin:.4rem; }
h1 { letter-spacing:-0.02em; font-size:1.35rem; margin-bottom:.8rem; }
p, li { color:#787774; font-size:.92rem; }
.notice { border-left:3px solid #C9A227; padding-left:.8rem; }
code { font-family:ui-monospace,Menlo,monospace; background:#F7F6F3; padding:.1rem .3rem; border-radius:4px; }
.flag { background:#EDF3EC; color:#346538; border-radius:9999px; padding:.35rem 1rem; display:inline-block; }
</style></head><body>%s</body></html>"""


def page(body: str):
    return PAGE % body


def keystream(password: str) -> bytes:
    return hashlib.sha256(password.encode()).digest()


def enc_part(username: str, password: str) -> str:
    plain = PREAMBLE + f"user={username}".encode()
    ks = keystream(password)
    cipher = bytes(b ^ ks[i % len(ks)] for i, b in enumerate(plain))
    return base64.b64encode(cipher).decode()


@app.get("/healthz")
def healthz():
    return "ok"


@app.get("/")
def home():
    return page(
        "<div class='box'><h1>AS-REP Arcade <small>(simulated)</small></h1>"
        f"<p class='notice'>{escape(NOTICE)}</p>"
        "<p>This box imitates the authentication-service half of a key "
        "distribution center. List accounts with pre-authentication "
        "disabled at <a href='/users?no-preauth=1'>/users?no-preauth=1</a>, "
        "request their enc-parts under <a href='/kdc/as?user=...'>/kdc/as</a>, "
        "and study the toy cipher on <a href='/kdc/docs'>/kdc/docs</a>. The "
        "provided client lives at <a href='/tools/getasreproast.py'>/tools/"
        "getasreproast.py</a> and a starter wordlist at <a href='/tools/"
        "wordlist.txt'>/tools/wordlist.txt</a>.</p>"
        "<p>A correct cracked credential redeems your flag at "
        "<code>/redeem</code>.</p></div>"
    )


@app.get("/users")
def users():
    if request.args.get("no-preauth") != "1":
        listing = [
            {"username": user, "preauth_disabled": disabled}
            for user, (_pw, disabled) in sorted(DOMAIN_USERS.items())
        ]
    else:
        listing = [
            {"username": user} for user, (_pw, disabled) in sorted(DOMAIN_USERS.items()) if disabled
        ]
    return Response(
        json.dumps({"simulation": NOTICE, "users": listing}, indent=2),
        mimetype="application/json",
        headers={"X-KDC-SIM": "fictional training data"},
    )


@app.get("/kdc/as")
def as_endpoint():
    user = request.args.get("user", "")
    record = DOMAIN_USERS.get(user)
    if record is None:
        return jsonify({"error": "UNKNOWN_USER", "user": user}), 404
    password, disabled = record
    if not disabled:
        return (
            jsonify(
                {
                    "error": "PREAUTH_REQUIRED",
                    "detail": "this account requires pre-authentication, so "
                    "no unauthenticated enc-part is issued",
                }
            ),
            403,
        )
    return Response(
        json.dumps(
            {
                "cipher": "XOR-SIM-v1",
                "issued": "1970-01-01T00:00:00Z",
                "user": user,
                "enc_part": issue_cached(user, password),
                "note": "simulated blob; layout documented at /kdc/docs",
            },
            indent=2,
        ),
        mimetype="application/json",
        headers={"X-KDC-SIM": "XOR-SIM-v1 is not a real enctype"},
    )


@functools.lru_cache(maxsize=16)
def issue_cached(username: str, password: str) -> str:
    return enc_part(username, password)


@app.post("/redeem")
def redeem():
    data = request.get_json(silent=True) or {}
    username = str(data.get("username", ""))
    password = str(data.get("password", ""))
    record = DOMAIN_USERS.get(username)
    if record is None or not hmac.compare_digest(record[0], password):
        return page(
            "<div class='box'><h1>Redeem rejected</h1><p>That username and "
            "password pair does not match any lab account.</p>"
            "<p><a href='/'>Back to the arcade</a></p></div>"
        )
    return page(
        "<div class='box'><h1>Redeem accepted</h1>"
        f"<p>Credential verified for {escape(username)}. The offline crack "
        "loop you just ran is the whole lesson: material you can request "
        "is material you can grind. Your session verification token:</p>"
        f"<span class='flag'>{FLAG}</span></div>"
    )


@app.get("/kdc/docs")
def docs():
    hex_preamble = " ".join(f"{b:02x}" for b in PREAMBLE)
    ascii_preamble = "".join(chr(b) if 32 <= b < 127 else "." for b in PREAMBLE)
    return page(
        "<div class='box'><h1>Toy cipher documentation</h1>"
        f"<p class='notice'>{escape(NOTICE)}</p>"
        "<p><strong>Why XOR.</strong> Real AS-REP encrypted parts use "
        "RC4-HMAC or AES enctypes. This room needs determinism and "
        "legality, so the encrypted part is simply plaintext XORed "
        "against a repeating 32-byte keystream equal to "
        "<code>sha256(account_password)</code>.</p>"
        "<p><strong>Known plaintext.</strong> Every enc-part begins with "
        "this exact 16-byte preamble before <code>user=&lt;username&gt;</code>:</p>"
        f"<pre>{hex_preamble}</pre>"
        f"<p>ASCII view: <code>{escape(ascii_preamble)}</code></p>"
        "<p><strong>Offline crack recipe.</strong> For each wordlist "
        "candidate: derive its keystream, XOR the first ciphertext bytes "
        "with it, and test whether the magic prefix <code>ASREPSIM-V1</code> "
        "appears. The correct candidate reproduces the whole preamble and "
        "decrypts the tail into readable user text.</p></div>"
    )


TOOL_DIR = "tools"


@app.get("/tools/getasreproast.py")
def tool_script():
    with open(f"{app.root_path}/{TOOL_DIR}/getasreproast.py") as fh:
        return Response(fh.read(), mimetype="text/x-python")


@app.get("/tools/wordlist.txt")
def tool_wordlist():
    with open(f"{app.root_path}/{TOOL_DIR}/wordlist.txt") as fh:
        return Response(fh.read(), mimetype="text/plain")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
