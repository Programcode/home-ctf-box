"""Fake KDC for the ticket-booth room: Kerberoasting mechanics, simulated.

The cryptography here is deliberately a toy. Real TGS enc-parts use
RC4-HMAC or AES enctypes; this room substitutes XOR against a keystream
derived from sha256(service-account password). That choice is disclosed
on /kdc/docs, keeps the room deterministic, and removes any legal gray
area: nothing here speaks Kerberos or touches real credentials.

Plaintext layout of every simulated ticket:

  bytes 0..47   PREAMBLE (constant, documented verbatim on /kdc/docs)
  bytes 48..    the requested SPN as UTF-8

The 48-byte constant prefix is what makes the offline crack teachable:
known plaintext over the full 32-byte keystream period.
"""

import base64
import functools
import hashlib
import json
import os
from pathlib import Path

from flask import Flask, Response, request
from markupsafe import escape

app = Flask(__name__)
FLAG = os.environ["ROOM_FLAG"]

PREAMBLE = b"KDCSIM-TGS-V1\x00" + b"\x00" * 18 + b"REALM-LAB.LOCAL\x00"
assert len(PREAMBLE) == 48

SERVICE_ACCOUNTS = {
    "MSSQLSvc/sql01.lab.local:1433": ("svc_sql", "SQLservice2019"),
    "HTTP/intranet.lab.local": ("svc_web", "fT7#qWz2!vLd9pRx"),
}

NOTICE = (
    "Simulation notice: this KDC is a Flask endpoint speaking JSON, not "
    "the Kerberos protocol. Ticket blobs are XOR stand-ins with a "
    "documented plaintext layout; no real credentials exist."
)

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Lab Ticket Booth</title>
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


@functools.lru_cache(maxsize=64)
def issue_ticket(spn: str) -> dict:
    account, password = SERVICE_ACCOUNTS[spn]
    plain = PREAMBLE + spn.encode()
    ks = keystream(password)
    cipher = bytes(b ^ ks[i % len(ks)] for i, b in enumerate(plain))
    return {
        "cipher": "XOR-SIM-v1",
        "issued": "1970-01-01T00:00:00Z",
        "spn": spn,
        "account": account,
        "enc_part": base64.b64encode(cipher).decode(),
        "note": "simulated blob; layout documented at /kdc/docs",
    }


@app.get("/healthz")
def healthz():
    return "ok"


@app.get("/")
def home():
    return page(
        "<div class='box'><h1>Lab Ticket Booth <small>(simulated)</small></h1>"
        f"<p class='notice'>{escape(NOTICE)}</p>"
        "<p>This box imitates the service-ticket half of a key distribution "
        "center. List every registered SPN at <a href='/kdc/spns'>/kdc/spns</a>, "
        "request tickets for each one under <a href='/kdc/tgs?spn=...'>"
        "/kdc/tgs</a>, and study the toy cipher on <a href='/kdc/docs'>"
        "/kdc/docs</a>. The provided client lives at <a href='/tools/"
        "getuserspns.py'>/tools/getuserspns.py</a> and a starter wordlist "
        "at <a href='/tools/wordlist.txt'>/tools/wordlist.txt</a>.</p>"
        "<p>The admin console at <code>/kdc/admin</code> accepts only a "
        "valid service-account sign-in.</p></div>"
    )


@app.get("/kdc/spns")
def spns():
    body = [
        {"spn": spn, "account": account} for spn, (account, _pw) in sorted(SERVICE_ACCOUNTS.items())
    ]
    return Response(
        json.dumps({"simulation": NOTICE, "spns": body}, indent=2),
        mimetype="application/json",
        headers={"X-KDC-SIM": "fictional training data"},
    )


@app.get("/kdc/tgs")
def tgs():
    spn = request.args.get("spn", "")
    if spn not in SERVICE_ACCOUNTS:
        return page(
            "<div class='box'><h1>Unknown SPN</h1><p>No service account is "
            f"registered for {escape(spn)!r}.</p>"
            "<p><a href='/'>Back to the booth</a></p></div>"
        )
    return Response(
        json.dumps(issue_ticket(spn), indent=2),
        mimetype="application/json",
        headers={"X-KDC-SIM": "XOR-SIM-v1 is not a real enctype"},
    )


@app.get("/kdc/docs")
def docs():
    hex_preamble = " ".join(f"{b:02x}" for b in PREAMBLE)
    ascii_preamble = "".join(chr(b) if 32 <= b < 127 else "." for b in PREAMBLE)
    return page(
        "<div class='box'><h1>Toy cipher documentation</h1>"
        f"<p class='notice'>{escape(NOTICE)}</p>"
        "<p><strong>Why XOR.</strong> Real TGS encrypted parts use "
        "RC4-HMAC or AES enctypes. This room needs determinism and "
        "legality, so the encrypted part is simply plaintext XORed "
        "against a repeating 32-byte keystream equal to "
        "<code>sha256(service_account_password)</code>.</p>"
        "<p><strong>Known plaintext.</strong> Every ticket begins with "
        "this exact 48-byte preamble before the SPN:</p>"
        f"<pre>{hex_preamble}</pre>"
        f"<p>ASCII view: <code>{escape(ascii_preamble)}</code></p>"
        "<p><strong>Offline crack recipe.</strong> For each wordlist "
        "candidate: derive its keystream, XOR the first ciphertext bytes "
        "with it, and test whether the magic prefix "
        "<code>KDCSIM-TGS-V1</code> appears. The correct candidate "
        "reproduces the whole preamble.</p></div>"
    )


@app.get("/kdc/admin")
def admin_console():
    auth = request.authorization
    if (
        auth is None
        or auth.type != "basic"
        or SERVICE_ACCOUNTS["MSSQLSvc/sql01.lab.local:1433"] != (auth.username, auth.password)
    ):
        return Response(
            page(
                "<div class='box'><h1>KDC-SIM admin console</h1>"
                "<p>Service-account sign-in required.</p></div>"
            ),
            401,
            {"WWW-Authenticate": 'Basic realm="KDC-SIM admin console"'},
        )
    return page(
        "<div class='box'><h1>KDC-SIM admin console</h1>"
        f"<p>Signed in as {escape(auth.username)}. Key material is safe "
        "and the console has nothing else to show except your session "
        "verification token:</p>"
        f"<span class='flag'>{FLAG}</span></div>"
    )


TOOL_DIR = Path(__file__).resolve().parent / "tools"


@app.get("/tools/getuserspns.py")
def tool_script():
    script = (TOOL_DIR / "getuserspns.py").read_text()
    return Response(script, mimetype="text/x-python")


@app.get("/tools/wordlist.txt")
def tool_wordlist():
    words = (TOOL_DIR / "wordlist.txt").read_text()
    return Response(words, mimetype="text/plain")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
