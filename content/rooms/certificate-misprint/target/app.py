"""Fake AD CS for the certificate-misprint room: ESC1 mechanics, simulated.

Real certificates are X.509 documents signed with RSA or ECDSA under
proper padding. This room substitutes textbook toy RSA with documented
512-bit keys hardcoded below: signature = SHA-256 digest of a canonical
field string raised to d mod n, verification raises it to e mod n and
compares digests. The choice is disclosed on /ca/docs, keeps the room
deterministic, and removes any legal gray area: nothing here speaks
real PKI or Kerberos protocol bytes, and all principals are fictional
training labels.

The vulnerability being taught is ESC1-shaped: a template that allows
the enrollee to supply the SAN lets the enrollee become anyone.
"""

import base64
import hashlib
import hmac
import json
import os

from flask import Flask, Response, jsonify, request
from markupsafe import escape

app = Flask(__name__)
FLAG = os.environ["ROOM_FLAG"]

# Toy RSA public material (512-bit). Documented as a stand-in for real
# PKI; never use numbers like these anywhere real.
N = 10736492858315762255065912477957052346317618628436429644068163419293111392208646089576607148571439470227624632114443906026593832664147597141472110855072661
E = 65537
# Private exponent stays server-side; its size is part of the disclosure.
D = 159563972168386597440136087302289836051594680014298525616405864937233783908494732211894493801832120475002316818281731386759810532624346011723434967592257

ENROLLMENT_USERS = {
    "labuser": "LabEnroll2026!",
}

TEMPLATES = {
    "UserAuth-Signing": {
        "san_from_request": False,
        "enrollment": "domain users",
        "note": "healthy template: SAN comes from the requester identity",
    },
    "WebEnroll-2023": {
        "san_from_request": True,
        "enrollment": "domain users",
        "note": "misconfigured: any authenticated enrollee may set the SAN",
    },
}

NOTICE = (
    "Simulation notice: this CA is a Flask endpoint speaking JSON, not "
    "AD CS or the Kerberos PKINIT protocol. Certificates are toy-RSA "
    "signed JSON blobs with documented 512-bit keys; no real PKI exists "
    "here."
)

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Certificate Misprint</title>
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


def canonical(serial: int, subject: str, san: str, template: str) -> str:
    return f"{serial}|{subject}|{san}|{template}"


def sign_message(message: str) -> str:
    digest = int.from_bytes(hashlib.sha256(message.encode()).digest(), "big")
    return format(pow(digest, D, N), "x")


def verify(cert: dict) -> bool:
    try:
        serial = int(str(cert["serial"]))
        subject = cert["subject"]
        san = cert["san"]
        template = cert["template"]
        sig = int(str(cert["sig"]), 16)
    except (KeyError, TypeError, ValueError):
        return False
    message = canonical(serial, subject, san, template)
    expected = int.from_bytes(hashlib.sha256(message.encode()).digest(), "big")
    # Public-key verification, no secret-dependent branching.
    return pow(sig % N, E, N) == expected


def issue(template: str, subject: str, san: str) -> dict:
    fields = f"{subject}|{san}|{template}"
    serial = int(hashlib.sha256(fields.encode()).hexdigest()[:12], 16)
    cert = {
        "serial": str(serial),
        "subject": subject,
        "san": san,
        "template": template,
        "sig": sign_message(canonical(serial, subject, san, template)),
    }
    cert["cert_token"] = base64.b64encode(json.dumps(cert, sort_keys=True).encode()).decode()
    return cert


@app.get("/healthz")
def healthz():
    return "ok"


@app.get("/")
def home():
    return page(
        "<div class='box'><h1>Lab Certificate Authority <small>(simulated)</small></h1>"
        f"<p class='notice'>{escape(NOTICE)}</p>"
        "<p>This box imitates the enrollment half of AD CS. Browse "
        "<a href='/ca/templates'>/ca/templates</a>, read the toy signing "
        "scheme at <a href='/ca/docs'>/ca/docs</a>, fetch the public key "
        "from <a href='/ca/pubkey'>/ca/pubkey</a>, and enroll at "
        "<code>/ca/enroll</code>. The admin page at <code>/admin</code> "
        "accepts only cert-tokens whose verified SAN reads administrator."
        "</p></div>"
    )


@app.get("/ca/templates")
def templates():
    body = [{"name": name, **record} for name, record in sorted(TEMPLATES.items())]
    return Response(
        json.dumps({"simulation": NOTICE, "templates": body}, indent=2),
        mimetype="application/json",
        headers={"X-CA-SIM": "fictional training data"},
    )


@app.post("/ca/enroll")
def enroll():
    auth = request.authorization
    data = request.get_json(silent=True) or {}
    template_name = str(data.get("template", ""))
    requested_san = data.get("san")
    if auth is None or auth.type != "basic":
        return jsonify({"error": "AUTH_REQUIRED", "detail": "enrollment credentials required"}), 401
    password = ENROLLMENT_USERS.get(auth.username)
    if password is None or not hmac.compare_digest(password, auth.password):
        return jsonify({"error": "BAD_ENROLLMENT_CREDENTIALS"}), 401
    template = TEMPLATES.get(template_name)
    if template is None:
        return jsonify({"error": "UNKNOWN_TEMPLATE", "template": template_name}), 404
    subject = f"CN={auth.username}"
    san = subject[len("CN=") :]
    if requested_san is not None:
        if not template["san_from_request"]:
            return (
                jsonify(
                    {
                        "error": "SAN_NOT_ALLOWED",
                        "detail": f"template {template_name} derives the SAN from "
                        "the requester identity",
                    }
                ),
                400,
            )
        san = str(requested_san)
    cert = issue(template_name, subject, san)
    cert["simulation"] = NOTICE
    return Response(
        json.dumps(cert, indent=2),
        mimetype="application/json",
        headers={"X-CA-SIM": "toy RSA, not X.509"},
    )


@app.get("/ca/pubkey")
def pubkey():
    return Response(
        json.dumps({"algorithm": "toy-rsa-512", "n": N, "e": E}, indent=2),
        mimetype="application/json",
        headers={"X-CA-SIM": "disclosed simulation key material"},
    )


@app.get("/admin")
def admin():
    token = request.headers.get("X-Client-Cert-SIM", "")
    cert = None
    if token:
        try:
            cert = json.loads(base64.b64decode(token.encode()))
        except (ValueError, json.JSONDecodeError):
            cert = None
    if not isinstance(cert, dict):
        return page(
            "<div class='box'><h1>Admin page</h1><p>Present an enrolled "
            "cert-token in the X-Client-Cert-SIM header.</p></div>"
        ), 401
    if not verify(cert):
        return page(
            "<div class='box'><h1>Invalid certificate</h1>"
            "<p>The cert-token failed signature verification against the "
            "published public key.</p></div>"
        ), 400
    if cert.get("san") != "administrator":
        return page(
            "<div class='box'><h1>Insufficient principal</h1>"
            "<p>Certificate SAN is "
            + escape(str(cert.get("san")))
            + ", not administrator.</p></div>"
        ), 403
    return page(
        "<div class='box'><h1>Admin page</h1>"
        "<p>Certificate accepted: signed by CA-SIM, SAN "
        f"{escape(cert['san'])}, issued to {escape(cert['subject'])}. One "
        "template checkbox turned an ordinary user into whoever they "
        "typed. Your session verification token:</p>"
        f"<span class='flag'>{FLAG}</span></div>"
    )


@app.get("/ca/docs")
def docs():
    return page(
        "<div class='box'><h1>Toy signing documentation</h1>"
        f"<p class='notice'>{escape(NOTICE)}</p>"
        "<p><strong>Scheme.</strong> A certificate is JSON with fields "
        "serial, subject, san, template, sig. The signature covers the "
        "canonical string <code>&lt;serial&gt;|&lt;subject&gt;|&lt;san&gt;|"
        "&lt;template&gt;</code>: digest it with SHA-256, interpret as a "
        "big-endian integer, raise to d mod n. Verification raises sig to "
        "<code>e=65537</code> modulo the 512-bit <code>n</code> published "
        "at /ca/pubkey and compares digests.</p>"
        "<p><strong>Disclosure.</strong> This is textbook RSA without "
        "padding, with keys small enough to print in source, hardcoded in "
        "this room on purpose. It is neither X.509 nor a real CSP, and it "
        "must never be copied outside training labs. Real ESC1 abuse uses "
        "full PKCS#7 issuance over Kerberos or NTLM enrollment channels; "
        "the logic flaw being rehearsed here is identical.</p>"
        "<p><strong>The misconfiguration.</strong> In AD CS terms the "
        "dangerous combination is a template whose ENROLLEE_SUPPLIES_"
        "SUBJECT flag is set, whose enrollment rights are broad, and "
        "whose resulting cert can authenticate. WebEnroll-2023 carries "
        "that shape: enrollment open to domain users plus a caller-"
        "supplied SAN.</p></div>"
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
