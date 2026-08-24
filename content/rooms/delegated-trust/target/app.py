"""Fake domain controller for the delegated-trust room: S4U mechanics, simulated.

Real constrained delegation is a two-protocol dance: S4U2Self gets a
service ticket to the service itself as some other principal, and
S4U2Proxy exchanges that ticket for one to a downstream service. This
room collapses both steps into one documented endpoint that mints a
signed JSON token. The signature is deliberately a toy: HMAC-SHA256
under a fixed secret printed on /dc/docs, standing in for
PAC-bearing Kerberos tickets. Nothing here speaks the Kerberos
protocol and no real credentials exist; every account is a fictional
training label.
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

# Fixed, disclosed room secret backing the toy token signatures.
TOY_SECRET = "DCSIM-DELEGATION-V1"

SERVICE_ACCOUNTS = {
    "svc_web": {
        "password": "WebDeleg@te26",
        "spn": "HTTP/dc01.lab.local",
        "allowed_to_impersonate": ["administrator"],
    },
    "svc_print": {
        "password": "PrintQueue77!",
        "spn": "CIFS/printer01.lab.local",
        "allowed_to_impersonate": [],
    },
}

RECON_FILES = {
    "/recon/files/web-config.bak": (
        "# simulated leftover from an earlier engagement phase\n"
        "[app:intranet]\n"
        "connection=server=sql01.lab.local;database=intranet;"
        "uid=svc_web;pwd=WebDeleg@te26\n"
    ),
}

NOTICE = (
    "Simulation notice: this DC is a Flask endpoint speaking JSON, not "
    "the Kerberos protocol. Impersonation tokens are HMAC-signed JSON "
    "stand-ins with a disclosed room secret; no real credentials exist."
)

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Delegated Trust</title>
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


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def mint_token(service: str, impersonate: str) -> str:
    payload = {"sim": "s4u", "service": service, "impersonate": impersonate}
    body = _b64url(json.dumps(payload, sort_keys=True).encode())
    sig = hmac.new(TOY_SECRET.encode(), body.encode(), hashlib.sha256).hexdigest()
    return f"S4USIM.v1.{body}.{sig}"


def read_token(token: str) -> dict | None:
    parts = token.split(".")
    if len(parts) != 4 or parts[0] != "S4USIM" or parts[1] != "v1":
        return None
    expected = hmac.new(TOY_SECRET.encode(), parts[2].encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, parts[3]):
        return None
    padded = parts[2] + "=" * (-len(parts[2]) % 4)
    try:
        payload = json.loads(base64.urlsafe_b64decode(padded.encode()))
    except (ValueError, json.JSONDecodeError):
        return None
    if payload.get("sim") != "s4u":
        return None
    return payload


@app.get("/healthz")
def healthz():
    return "ok"


@app.get("/")
def home():
    return page(
        "<div class='box'><h1>Lab Domain Controller <small>(simulated)</small></h1>"
        f"<p class='notice'>{escape(NOTICE)}</p>"
        "<p>This box imitates the delegation half of a domain controller. "
        "Artifacts from an earlier recon phase live under <a href='/recon/"
        "index'>/recon/index</a>, the delegation configuration is public at "
        "<a href='/delegation/config'>/delegation/config</a>, the simulated "
        "S4U flow is documented at <a href='/dc/docs'>/dc/docs</a>, and the "
        "admin-only resource waits at <a href='/dc/admin-only'>/dc/admin-only"
        "</a>.</p></div>"
    )


@app.get("/recon/index")
def recon_index():
    listing = [
        {"path": path, "note": note}
        for path, note in [
            ("/recon/files/web-config.bak", "web server config backup, phase 2 recon"),
        ]
    ]
    return Response(
        json.dumps({"simulation": NOTICE, "artifacts": listing}, indent=2),
        mimetype="application/json",
        headers={"X-DC-SIM": "fictional training data"},
    )


@app.get("/recon/files/<path:name>")
def recon_file(name):
    key = f"/recon/files/{name}"
    text = RECON_FILES.get(key)
    if text is None:
        return page("<div class='box'><h1>No such artifact</h1></div>"), 404
    return Response(text, mimetype="text/plain")


@app.get("/delegation/config")
def delegation_config():
    body = [
        {
            "account": user,
            "spn": record["spn"],
            "allowed_to_impersonate": record["allowed_to_impersonate"],
        }
        for user, record in sorted(SERVICE_ACCOUNTS.items())
    ]
    return Response(
        json.dumps({"simulation": NOTICE, "delegation": body}, indent=2),
        mimetype="application/json",
        headers={"X-DC-SIM": "fictional training data"},
    )


@app.get("/tgs")
def tgs():
    auth = request.authorization
    target = request.args.get("impersonate", "")
    if auth is None or auth.type != "basic":
        return (
            jsonify({"error": "AUTH_REQUIRED", "detail": "service credentials required"}),
            401,
        )
    record = SERVICE_ACCOUNTS.get(auth.username)
    if record is None or not hmac.compare_digest(record["password"], auth.password):
        return jsonify({"error": "BAD_SERVICE_CREDENTIALS"}), 401
    if target not in record["allowed_to_impersonate"]:
        return (
            jsonify(
                {
                    "error": "DELEGATION_NOT_PERMITTED",
                    "detail": f"{auth.username} may not impersonate {target!r}",
                }
            ),
            403,
        )
    return Response(
        json.dumps(
            {
                "simulation": NOTICE,
                "flow": "S4USIM (collapsed S4U2Self+S4U2Proxy)",
                "service": auth.username,
                "impersonate": target,
                "token": mint_token(auth.username, target),
            },
            indent=2,
        ),
        mimetype="application/json",
        headers={"X-DC-SIM": "token is not a real service ticket"},
    )


@app.get("/dc/admin-only")
def admin_only():
    header = request.headers.get("Authorization", "")
    token = header[7:] if header.startswith("Bearer ") else ""
    payload = read_token(token) if token else None
    if payload is None:
        return page(
            "<div class='box'><h1>DC-SIM admin resource</h1>"
            "<p>A valid Bearer token minted by the /tgs flow is required."
            "</p></div>"
        ), 401
    if payload.get("impersonate") != "administrator":
        return page(
            "<div class='box'><h1>Insufficient delegation</h1>"
            "<p>Token impersonates "
            + escape(str(payload.get("impersonate")))
            + ", not administrator.</p></div>"
        ), 403
    return page(
        "<div class='box'><h1>DC-SIM admin resource</h1>"
        "<p>Acting as administrator on behalf of "
        f"{escape(payload['service'])}. Delegation configured this broadly "
        "is how a single web server becomes the whole domain. Your session "
        "verification token:</p>"
        f"<span class='flag'>{FLAG}</span></div>"
    )


@app.get("/dc/docs")
def docs():
    return page(
        "<div class='box'><h1>S4USIM protocol documentation</h1>"
        f"<p class='notice'>{escape(NOTICE)}</p>"
        "<p><strong>Token format.</strong> Tokens look like "
        "<code>S4USIM.v1.&lt;base64url payload&gt;.&lt;hex HMAC&gt;</code>. "
        'The payload is JSON such as <code>{"sim":"s4u",'
        '"service":"svc_web","impersonate":"administrator"}</code>. '
        "The signature is HMAC-SHA256 under the fixed room secret "
        f"<code>{escape(TOY_SECRET)}</code>, printed here because this is a "
        "disclosed simulation, not a real PAC.</p>"
        "<p><strong>What it stands in for.</strong> Real constrained "
        "delegation runs two protocols: S4U2Self returns a ticket to the "
        "service as another principal without their password, and S4U2Proxy "
        "exchanges that ticket for one to a downstream service listed in "
        "msDS-AllowedToDelegateTo. The KDC enforces that list per hop. Here "
        "both hops collapse into GET /tgs?impersonate=&lt;user&gt; with the "
        "service's own Basic credentials, and /dc/admin-only enforces the "
        "allowlist by reading the verified payload.</p></div>"
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
