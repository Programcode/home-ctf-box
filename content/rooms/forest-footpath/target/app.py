"""Two-domain trust simulation behind one front controller. Room target only.

One container plays two domains. child.corp and parent.corp are separate
Flask apps bound to distinct loopback ports; the front controller on port
8000 forwards by Host header, the way a reverse proxy fronts several
internal sites. Nothing here is real Active Directory.
"""

import hashlib
import hmac
import http.client
import os
import threading

from flask import Flask, Response, jsonify, request
from werkzeug.serving import make_server

ROOM_FLAG = os.environ.get("ROOM_FLAG", "FLAG{FLAGNOTSET0000000000000000}")
TOKEN_KEY = b"forest-footpath-lab-hmac-key"
CHILD_USER = "learner"
CHILD_PASS = "learner"

child = Flask("child.corp")
parent = Flask("parent.corp")
front = Flask("front")


def _mint(prefix: str, material: str) -> str:
    digest = hmac.new(TOKEN_KEY, material.encode(), hashlib.sha256).hexdigest()[:16]
    return f"{prefix}-{digest}"


CHILD_TOKEN = _mint("childtok", f"{CHILD_USER}|DA-child|{CHILD_PASS}")
PARENT_TOKEN = _mint("parenttok", "child-corpus|enterprise-sim")


# --- child.corp domain API (loopback 9011) ---

TRUST_DOC = {
    "domain": "child.corp",
    "simulated": True,
    "trusts": [
        {
            "partner": "parent.corp",
            "type": "forest-parent-child-sim",
            "direction": "bidirectional",
            "transitive": True,
            "notes": (
                "Within a forest the parent-child link is transitive. A "
                "principal holding Domain Admins in child.corp has a "
                "documented path into enterprise scope on parent.corp. "
                "This API mints childtok-... bearer tokens for members of "
                "DA-child; the parent exposes /trust-exchange for exactly "
                "these tokens."
            ),
        }
    ],
    "endpoints": {
        "GET /": "this overview",
        "GET /trusts": "trust documentation",
        "POST /auth": '{"user","password"} -> bearer token',
    },
}


@child.get("/healthz")
def child_health() -> Response:
    return jsonify(status="ok")


@child.get("/")
def child_home() -> Response:
    return jsonify(TRUST_DOC | {"endpoints": TRUST_DOC["endpoints"]})


@child.get("/trusts")
def child_trusts() -> Response:
    return jsonify(TRUST_DOC)


@child.post("/auth")
def child_auth() -> tuple[Response, int] | Response:
    body = request.get_json(silent=True) or {}
    if body.get("user") == CHILD_USER and body.get("password") == CHILD_PASS:
        return jsonify(
            token=CHILD_TOKEN,
            user=CHILD_USER,
            groups=["DA-child"],
            note="member of child Domain Admins (simulated)",
        )
    return jsonify(error="invalid credentials"), 401


# --- parent.corp domain API (loopback 9012) ---

PARENT_DOC = {
    "domain": "parent.corp",
    "simulated": True,
    "forest_root": True,
    "inbound_trust": (
        "child.corp tokens are accepted at POST /trust-exchange because "
        "the forest trust is transitive. Exchange a childtok-... for a "
        "parenttok-... scoped enterprise-sim, then present it as Bearer "
        "auth to GET /enterprise/path."
    ),
    "endpoints": {
        "GET /": "this overview",
        "GET /trusts": "trust documentation",
        "POST /trust-exchange": '{"child_token"} -> enterprise-scoped token',
        "GET /enterprise/path": "Bearer auth -> enterprise scope contents",
    },
}


@parent.get("/healthz")
def parent_health() -> Response:
    return jsonify(status="ok")


@parent.get("/")
def parent_home() -> Response:
    return jsonify(PARENT_DOC)


@parent.get("/trusts")
def parent_trusts() -> Response:
    return jsonify(PARENT_DOC)


@parent.post("/trust-exchange")
def trust_exchange() -> tuple[Response, int]:
    body = request.get_json(silent=True) or {}
    token = str(body.get("child_token", ""))
    if not hmac.compare_digest(token, CHILD_TOKEN):
        return jsonify(error="unknown or invalid child token"), 401
    return jsonify(
        token=PARENT_TOKEN,
        scope="enterprise-sim",
        note="issued under the transitive forest trust with child.corp",
    )


@parent.get("/enterprise/path")
def enterprise_path() -> tuple[Response, int]:
    auth = request.headers.get("Authorization", "")
    presented = auth.removeprefix("Bearer ").strip()
    if not hmac.compare_digest(presented, PARENT_TOKEN):
        return jsonify(error="enterprise scope requires the parent token"), 401
    return jsonify(
        reached=True,
        path="child.corp DA -> forest trust -> parent.corp enterprise scope",
        flag=ROOM_FLAG,
    )


# --- front controller (0.0.0.0:8000) routes by Host header ---

BACKENDS = {
    "child.corp": ("127.0.0.1", 9011),
    "parent.corp": ("127.0.0.1", 9012),
}

LANDING = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Forest Footpath range front</title></head>
<body style="font-family:sans-serif;max-width:44rem;margin:3rem auto;line-height:1.5">
<h1>Simulated forest: child.corp and parent.corp</h1>
<p><strong>Disclosure:</strong> this is one Linux container, not a Windows
estate. The two domains are small JSON APIs bound to separate loopback ports
inside the box; the controller you are reading now proxies requests to them
by Host header, the way nginx fronts several internal sites.</p>
<p>Address a domain by sending its name as the Host header, for example:</p>
<pre>curl -H 'Host: child.corp' http://target:8000/trusts
curl -H 'Host: parent.corp' http://target:8000/</pre>
<p>Both APIs answer JSON and describe their routes on their landing pages.</p>
</body></html>"""


@front.get("/healthz")
def front_health() -> Response:
    return jsonify(status="ok")


@front.route("/", defaults={"path": ""}, methods=["GET", "POST"])
@front.route("/<path:path>", methods=["GET", "POST"])
def proxy(path: str) -> Response:
    host = (request.host.split(":")[0] or "").lower()
    backend = BACKENDS.get(host)
    if backend is None:
        return Response(LANDING, status=200, content_type="text/html")
    body = request.get_data()
    headers = {}
    if body:
        headers["Content-Type"] = request.content_type or "application/json"
    if request.headers.get("Authorization"):
        headers["Authorization"] = request.headers["Authorization"]
    conn = http.client.HTTPConnection(backend[0], backend[1], timeout=10)
    try:
        target = "/" + path
        if request.query_string:
            target += "?" + request.query_string.decode()
        conn.request(request.method, target, body=body if body else None, headers=headers)
        resp = conn.getresponse()
        payload = resp.read()
        ctype = resp.getheader("Content-Type") or "application/json"
        status = resp.status
    finally:
        conn.close()
    return Response(payload, status=status, content_type=ctype)


def _serve_in_thread(server: object) -> None:
    threading.Thread(target=server.serve_forever, daemon=True).start()  # type: ignore[attr-defined]


if __name__ == "__main__":
    _serve_in_thread(make_server("127.0.0.1", 9011, child))
    _serve_in_thread(make_server("127.0.0.1", 9012, parent))
    make_server("0.0.0.0", 8000, front).serve_forever()
