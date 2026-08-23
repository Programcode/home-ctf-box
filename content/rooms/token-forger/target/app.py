"""TokenForge: deliberately vulnerable JWT service. Room target only."""

import base64
import hashlib
import hmac
import json
import os

from flask import Flask, Response, request
from markupsafe import escape

app = Flask(__name__)
SECRET = "forge-dev-signing-key"
FLAG = os.environ["ROOM_FLAG"]

USERS = {
    "guest": "guest-pass",
    "admin": "7c1f0d9ab2e4",
}

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>TokenForge</title>
<style>
body { background:#F7F6F3; font-family:Helvetica,Arial,sans-serif; display:flex; justify-content:center; padding-top:12vh; }
.box { background:#fff; border:1px solid #EAEAEA; border-radius:8px; padding:2.5rem; width:28rem; }
h1 { letter-spacing:-0.02em; font-size:1.4rem; margin-bottom:.5rem; }
p { color:#787774; font-size:.88rem; }
code { font-family:ui-monospace,Menlo,monospace; font-size:.85rem; background:#F7F6F3; border:1px solid #EAEAEA; border-radius:4px; padding:.1rem .4rem; }
.flag { background:#EDF3EC; color:#346538; border-radius:9999px; padding:.35rem 1rem; display:inline-block; }
</style></head><body>__BODY__</body></html>"""


def b64url_encode(raw):
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def b64url_decode(segment):
    padded = segment + "=" * (-len(segment) % 4)
    return base64.urlsafe_b64decode(padded)


def sign(sections):
    return b64url_encode(hmac.new(SECRET.encode(), sections.encode(), hashlib.sha256).digest())


def admin_page(payload):
    who = escape(str(payload.get("sub", "unknown")))
    body = (
        '<div class="box"><h1>TokenForge Admin Console</h1>'
        f"<p>Signed in as {who}.</p>"
        f"<span class='flag'>{FLAG}</span></div>"
    )
    return PAGE.replace("__BODY__", body)


@app.get("/healthz")
def healthz():
    return "ok"


@app.get("/")
def index():
    body = (
        '<div class="box"><h1>TokenForge</h1>'
        "<p>Hand-rolled JWT issuance service.</p>"
        "<p><code>POST /login</code> with form fields <code>username</code> and "
        "<code>password</code> returns a signed HS256 token.</p>"
        "<p><code>GET /admin</code> with header "
        "<code>Authorization: Bearer &lt;token&gt;</code> opens the console.</p></div>"
    )
    return PAGE.replace("__BODY__", body)


@app.post("/login")
def login():
    username = request.form.get("username", "")
    password = request.form.get("password", "")
    if username not in USERS or USERS[username] != password:
        return Response('{"error": "invalid credentials"}', status=401, mimetype="application/json")
    role = "admin" if username == "admin" else "user"
    header = b64url_encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    payload = b64url_encode(json.dumps({"sub": username, "role": role}).encode())
    token = header + "." + payload + "." + sign(header + "." + payload)
    return {"token": token}


@app.get("/admin")
def admin():
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return Response("missing bearer token\n", status=401)
    parts = auth[7:].strip().split(".")
    if len(parts) != 3:
        return Response("malformed token\n", status=401)
    try:
        header = json.loads(b64url_decode(parts[0]))
        payload = json.loads(b64url_decode(parts[1]))
    except Exception:
        return Response("malformed token\n", status=401)
    # The flaw: the token chooses the algorithm the verifier will run.
    alg = header.get("alg")
    if alg == "none":
        if parts[2] == "" and payload.get("role") == "admin":
            return admin_page(payload)
        return Response("invalid token\n", status=401)
    if alg == "HS256":
        if not hmac.compare_digest(sign(parts[0] + "." + parts[1]), parts[2]):
            return Response("bad signature\n", status=401)
        if payload.get("role") == "admin":
            return admin_page(payload)
        return Response("admin access required\n", status=403)
    return Response("unsupported algorithm\n", status=401)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
