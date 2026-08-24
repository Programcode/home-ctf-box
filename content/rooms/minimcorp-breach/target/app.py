"""MinimCorp Breach: three simulated enterprise hosts behind one front controller.

Room target only. Single-container reality, disclosed to learners on the
landing page: vpn-edge.minimcorp.net, wiki.corp.minimcorp.net, and
finance.minimcorp.net are three small Flask apps bound to distinct loopback
ports inside this one container. The controller on port 8000 proxies by Host
header the way an nginx edge fronts a corporate estate. Each host guards one
four-character slice of this session's flag; the directory-sim token forge on
the finance host unlocks /scoreboard, which reassembles them.
"""

import base64
import hashlib
import hmac
import http.client
import os
import sqlite3
import threading

from flask import Flask, Response, jsonify, request
from werkzeug.serving import make_server

ROOM_FLAG = os.environ.get("ROOM_FLAG", "FLAG{FLAGNOTSET0000000000000000}")
BODY = ROOM_FLAG.removeprefix("FLAG{").removesuffix("}").ljust(20, "0")
FRAGS = {
    "vpn-edge.minimcorp.net": BODY[0:4],
    "wiki.corp.minimcorp.net": BODY[4:8],
    "finance.minimcorp.net": BODY[8:12],
}

WIKI_USER = "svc_wiki"
WIKI_PASS = "W1kiSync#2026"
FIN_API_KEY = "fin-api-key-7788"
SSO_SECRET = "minimcorp-sso-2026"
DOMAIN_ADMIN = "a.adams"
ADMIN_TOKEN = "dirt-" + hashlib.sha256((BODY + ":admin").encode()).hexdigest()[:16]

BACKEND_PORTS = {
    "vpn-edge.minimcorp.net": 9101,
    "wiki.corp.minimcorp.net": 9102,
    "finance.minimcorp.net": 9103,
}

edge = Flask("vpn-edge", static_folder=None)
wiki = Flask("wiki", static_folder=None)
finance = Flask("finance", static_folder=None)
front = Flask("front", static_folder=None)


# --- host 1: vpn-edge (loopback 9101), stale rollback config leak ---

CONFIG_PLAINTEXT = (
    "; minimcorp vpn edge rollback snapshot, 2026-05-12\n"
    "; kept for emergency restore only\n"
    "[ike]\n"
    "psk=Min!mVPN-PSK-rotate-me\n"
    "\n"
    "[internal]\n"
    "wiki=wiki.corp.minimcorp.net (basic auth)\n"
    f"wiki_user={WIKI_USER}\n"
    f"wiki_pass={WIKI_PASS}\n"
    f"\n"
    "; payout note from ops offsite: fragment[vpn-edge.minimcorp.net]="
    f"{FRAGS['vpn-edge.minimcorp.net']}\n"
    "; finance delegates sign-in to the directory sim; its legacy signing\n"
    "; secret lives in the wiki finance runbook, ask svc_wiki\n"
)
CONFIG_B64 = base64.b64encode(CONFIG_PLAINTEXT.encode())

EDGE_HOME = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>MinimCorp secure access portal</title></head>
<body style="font-family:sans-serif;max-width:44rem;margin:3rem auto;line-height:1.5">
<h1>MinimCorp secure access portal (vpn-edge)</h1>
<p>Authorized staff only. Connect with your corporate client profile.
Report anomalies to the service desk.</p>
<!-- ops note: rollback snapshot of the old gateway config still sits at
     /static/vpn.conf.bak (base64). deletion ticket INC-4471 keeps slipping. -->
</body></html>"""


@edge.get("/healthz")
def edge_health() -> Response:
    return jsonify(status="ok")


@edge.get("/")
def edge_home() -> Response:
    return Response(EDGE_HOME, content_type="text/html")


@edge.get("/static/vpn.conf.bak")
def edge_config() -> Response:
    return Response(CONFIG_B64, content_type="text/plain")


# --- host 2: wiki.corp (loopback 9102), basic auth intranet ---

_conn = sqlite3.connect(":memory:", check_same_thread=False)
_conn.execute("CREATE TABLE pages(slug TEXT, title TEXT, body TEXT)")
_conn.execute("CREATE TABLE revisions(page TEXT, rev INT, author TEXT, comment TEXT)")
_conn.executemany(
    "INSERT INTO pages VALUES (?, ?, ?)",
    [
        (
            "it-onboarding",
            "IT onboarding",
            "Welcome to MinimCorp. Badges, laptops, and the password manager "
            "orientation live here. Nothing sensitive.",
        ),
        (
            "lunch-rota",
            "Canteen rota",
            "Monday soup, Tuesday curry, Wednesday leftovers day.",
        ),
        (
            "finance-runbook",
            "Finance integration runbook",
            "The finance API authenticates integrations with a static key. "
            "Key: " + FIN_API_KEY + ". Endpoints: GET /api/invoices/<id> for "
            "invoice records keyed by numeric employee id, 1001 upward. "
            "Access control is applied at the gateway, not per record, so "
            "always request your own employee id. Sign-in is delegated to "
            "the minimcorp directory sim: POST /sso/verify with user, role, "
            "and sig, where sig = md5hex(user|role|secret). The legacy "
            "signing secret is " + SSO_SECRET + ", rotated never.",
        ),
    ],
)
_conn.executemany(
    "INSERT INTO revisions VALUES (?, ?, ?, ?)",
    [
        ("finance-runbook", 1, "svc_wiki", "initial import from confluence"),
        ("finance-runbook", 2, "f.okafor", "added invoice endpoint notes"),
        (
            "finance-runbook",
            3,
            "svc_wiki",
            "sync bot stamp: fragment[wiki.corp.minimcorp.net]="
            + FRAGS["wiki.corp.minimcorp.net"]
            + " ; embedded in revision metadata by design",
        ),
    ],
)
_conn.commit()


def _wiki_auth_ok() -> bool:
    auth = request.authorization
    return bool(auth and auth.username == WIKI_USER and auth.password == WIKI_PASS)


def _need_wiki_auth() -> tuple[Response, int] | None:
    if _wiki_auth_ok():
        return None
    return (
        jsonify(error="basic auth required", hint="the vpn edge leaks service creds"),
        401,
    )


@wiki.get("/healthz")
def wiki_health() -> Response:
    return jsonify(status="ok")


@wiki.get("/")
def wiki_home() -> tuple[Response, int]:
    blocked = _need_wiki_auth()
    if blocked:
        return blocked
    rows = _conn.execute("SELECT slug, title FROM pages").fetchall()
    return jsonify(space="MinimCorp internal", pages=[{"slug": s, "title": t} for s, t in rows])


@wiki.get("/pages/<slug>")
def wiki_page(slug: str) -> tuple[Response, int] | None:
    blocked = _need_wiki_auth()
    if blocked:
        return blocked
    row = _conn.execute("SELECT title, body FROM pages WHERE slug = ?", (slug,)).fetchone()
    if row is None:
        return jsonify(error="no such page"), 404
    return jsonify(slug=slug, title=row[0], body=row[1], revisions="/pages/" + slug + "/revisions")


@wiki.get("/pages/<slug>/revisions")
def wiki_revisions(slug: str) -> tuple[Response, int] | None:
    blocked = _need_wiki_auth()
    if blocked:
        return blocked
    rows = _conn.execute(
        "SELECT rev, author, comment FROM revisions WHERE page = ? ORDER BY rev", (slug,)
    ).fetchall()
    return jsonify(page=slug, revisions=[{"rev": r, "author": a, "comment": c} for r, a, c in rows])


# --- host 3: finance.minimcorp.net (loopback 9103), IDOR plus token forge ---

INVOICES = {
    1001: {"employee": "j.novak", "kind": "travel", "total": 412.5, "note": "prague trip"},
    1002: {"employee": "m.horvath", "kind": "equipment", "total": 1899.0, "note": "monitor"},
    1003: {"employee": "s.danh", "kind": "travel", "total": 220.75, "note": "train pass"},
    1007: {"employee": "p.kovacs", "kind": "training", "total": 650.0, "note": "course"},
    1009: {"employee": "r.mezei", "kind": "travel", "total": 98.4, "note": "taxi"},
    1013: {
        "employee": "e.szabo",
        "kind": "executive",
        "total": 18400.0,
        "note": (
            "board ledger extract. fragment[finance.minimcorp.net]="
            + FRAGS["finance.minimcorp.net"]
            + ". privileged estate actions require a directory-sim admin "
            "token issued to principal " + DOMAIN_ADMIN + " with role "
            "estate-admin."
        ),
    },
}


@finance.get("/healthz")
def fin_health() -> Response:
    return jsonify(status="ok")


@finance.get("/")
def fin_home() -> Response:
    return jsonify(
        service="minimcorp finance api sim",
        auth="X-API-Key header, integration keys issued via the wiki runbook",
        endpoints=["/api/invoices/<employee_id>", "/sso/verify", "/scoreboard"],
    )


def _api_key_ok() -> bool:
    return request.headers.get("X-API-Key", "") == FIN_API_KEY


@finance.get("/api/invoices/<int:employee_id>")
def fin_invoice(employee_id: int) -> tuple[Response, int] | Response:
    if not _api_key_ok():
        return jsonify(error="missing or invalid X-API-Key"), 401
    record = INVOICES.get(employee_id)
    if record is None:
        return jsonify(error="no invoice for that employee id"), 404
    return jsonify(employee_id=employee_id, **record)


@finance.post("/sso/verify")
def fin_sso() -> tuple[Response, int] | Response:
    body = request.get_json(silent=True) or {}
    user = str(body.get("user", ""))
    role = str(body.get("role", ""))
    sig = str(body.get("sig", ""))
    expected = hashlib.md5(f"{user}|{role}|{SSO_SECRET}".encode()).hexdigest()
    if hmac.compare_digest(sig, expected):
        if user == DOMAIN_ADMIN and role == "estate-admin":
            return jsonify(
                granted=True,
                principal=user,
                role=role,
                token=ADMIN_TOKEN,
                note="directory-sim admin token; present it to /scoreboard",
            )
        return jsonify(granted=True, principal=user, role=role, scope="self-service")
    return jsonify(error="signature verification failed"), 401


# --- front controller (0.0.0.0:8000): vhost proxy plus scoreboard ---

LANDING = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>MinimCorp range front</title></head>
<body style="font-family:sans-serif;max-width:46rem;margin:3rem auto;line-height:1.55">
<h1>This is ONE container playing three hosts</h1>
<p><strong>Disclosure:</strong> there is no corporate network here.
vpn-edge.minimcorp.net, wiki.corp.minimcorp.net, and finance.minimcorp.net
are three small APIs bound to separate loopback ports inside the same Linux
container. The process you are talking to proxies each request by Host
header, the way an edge proxy fronts an internal estate. Treat every host
as a labeled room inside one box.</p>
<p>Address any of them like this:</p>
<pre>curl -H 'Host: vpn-edge.minimcorp.net' http://target:8000/
curl -H 'Host: finance.minimcorp.net' http://target:8000/api/invoices/1001</pre>
<p>Each simulated host guards one four-character fragment. Recover all
three, forge a directory-sim admin token on the finance host, then POST
fragments plus token to /scoreboard to unlock the master flag.</p>
</body></html>"""


@front.get("/healthz")
def front_health() -> Response:
    return jsonify(status="ok")


@front.route("/", defaults={"path": ""}, methods=["GET", "POST"])
@front.route("/<path:path>", methods=["GET", "POST"])
def proxy(path: str) -> Response:
    host = (request.host.split(":")[0] or "").lower()
    port = BACKEND_PORTS.get(host)
    if port is None:
        return Response(LANDING, status=200, content_type="text/html")
    body = request.get_data()
    headers = {}
    if body:
        headers["Content-Type"] = request.content_type or "application/json"
    for name in ("Authorization", "X-API-Key"):
        if request.headers.get(name):
            headers[name] = request.headers[name]
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=15)
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


@front.get("/scoreboard")
def scoreboard_info() -> Response:
    return jsonify(
        usage=(
            'POST /scoreboard {"fragments": {"<host>": "<4 chars>"}, '
            '"token": "<directory-sim admin token>"}'
        ),
        hosts=sorted(FRAGS),
        note="three fragments plus a forged admin token unlock the master flag",
    )


@front.post("/scoreboard")
def scoreboard_submit() -> tuple[Response, int] | Response:
    body = request.get_json(silent=True) or {}
    submitted = body.get("fragments") or {}
    accepted = []
    wrong = []
    missing = []
    for host, frag in FRAGS.items():
        given = str(submitted.get(host, ""))
        if hmac.compare_digest(given.strip(), frag):
            accepted.append(host)
        elif given.strip():
            wrong.append(host)
        else:
            missing.append(host)
    if len(accepted) != len(FRAGS):
        return jsonify(status="locked", accepted=accepted, wrong=wrong, missing=missing)
    token = str(body.get("token", "")).strip()
    if not hmac.compare_digest(token, ADMIN_TOKEN):
        return jsonify(
            status="locked",
            accepted=accepted,
            error="fragments verified but the directory-sim admin token is missing or invalid",
        )
    return jsonify(
        status="unlocked",
        accepted=accepted,
        flag=ROOM_FLAG,
        note="all fragments and the forged admin token verified against this session's flag",
    )


def _serve_in_thread(server: object) -> None:
    threading.Thread(target=server.serve_forever, daemon=True).start()  # type: ignore[attr-defined]


if __name__ == "__main__":
    app_map = {
        "vpn-edge.minimcorp.net": edge,
        "wiki.corp.minimcorp.net": wiki,
        "finance.minimcorp.net": finance,
    }
    for hostname, port in BACKEND_PORTS.items():
        _serve_in_thread(make_server("127.0.0.1", port, app_map[hostname]))
    make_server("0.0.0.0", 8000, front).serve_forever()
