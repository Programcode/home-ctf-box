"""Full Spectrum: grand capstone, red chain plus blue deliverable, one container.

Room target only. Single-container reality, disclosed on the landing page:
portal.spectrum.io, git.internal.spectrum.io, core-db.spectrum.internal,
archive.spectrum.internal, and ir.spectrum.io are five simulated host APIs
on distinct loopback ports inside this one locked container, fronted by a
Host-header controller. The red chain runs initial access, pivot,
privilege, and exfil as a server-side state machine; the blue deliverable
grades a professional incident report against a rubric once the red chain
is complete. Everything resets on restart.
"""

import hashlib
import hmac
import http.client
import os
import threading

from flask import Flask, Response, jsonify, request
from werkzeug.serving import make_server

RED_FLAG = os.environ.get("ROOM_FLAG_RED_CHAIN", "FLAG{FLAGNOTSET0000000000000000}")
BLUE_FLAG = os.environ.get("ROOM_FLAG_BLUE_REPORT", "FLAG{FLAGNOTSET0000000000000000}")
BODY = RED_FLAG.removeprefix("FLAG{").removesuffix("}")

PORTAL_SESSION = "sess-" + hashlib.sha256((BODY + ":portal").encode()).hexdigest()[:12]
DEPLOY_KEY = "DBK-" + hashlib.sha256((BODY + ":dbk").encode()).hexdigest()[:16]
CONSOLE_TOKEN = "con-" + hashlib.sha256((BODY + ":console").encode()).hexdigest()[:12]
ADMIN_SID = "adm-" + hashlib.sha256((BODY + ":admin").encode()).hexdigest()[:12]
STAGING_DATASET = "ds-q3-ledgers"

BREACH_CORPUS = """# defanged partner-breach compilation, 2024 vintage
m.okafor@northwind.example:Summer2024!
j.petrov@helios.example:Welcome123!
e.reyes@spectrum.io:Tundra!Fall42
a.silva@atlas.example:Spring!22
k.novak@vertex.example:Passw0rd!
d.haugen@orbit.example:Winter2023!
"""

BACKEND_PORTS = {
    "portal.spectrum.io": 9101,
    "git.internal.spectrum.io": 9102,
    "core-db.spectrum.internal": 9103,
    "archive.spectrum.internal": 9104,
    "ir.spectrum.io": 9105,
}

red_state = {"stage": 0}  # 1 logged in, 2 pivoted, 3 privileged, 4 exfiltrated

portal = Flask("portal", static_folder=None)
git = Flask("git", static_folder=None)
coredb = Flask("core-db", static_folder=None)
archive = Flask("archive", static_folder=None)
ir = Flask("ir", static_folder=None)
front = Flask("front", static_folder=None)


def _red_complete() -> bool:
    return red_state["stage"] >= 4


# --- host 1: portal.spectrum.io (loopback 9101), initial access ---

PORTAL_HOME = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Spectrum partner portal</title></head>
<body style="font-family:sans-serif;max-width:44rem;margin:3rem auto;line-height:1.5">
<h1>Spectrum partner portal</h1>
<p>Accounts for logistics partners. Security notice: a 2024 breach at an
email vendor exposed partner passwords; our defanged copy of that corpus
is kept at /static/partner-breach.txt for exposure checks.</p>
<!-- intranet jump service for staff: GET /api/jump/git with your session header -->
<form action="/login" method="POST">
<input name="username" placeholder="partner email"><input name="password" type="password">
<button>sign in</button></form>
</body></html>"""


@portal.get("/healthz")
def portal_health() -> Response:
    return jsonify(status="ok")


@portal.get("/")
def portal_home() -> Response:
    return Response(PORTAL_HOME, content_type="text/html")


@portal.get("/static/partner-breach.txt")
def portal_corpus() -> Response:
    return Response(BREACH_CORPUS, content_type="text/plain")


@portal.post("/login")
def portal_login() -> tuple[Response, int] | Response:
    body = request.get_json(silent=True) or {}
    user = str(body.get("username", ""))
    password = str(body.get("password", ""))
    if user == "e.reyes@spectrum.io" and password == "Tundra!Fall42":
        if red_state["stage"] < 1:
            red_state["stage"] = 1
        return jsonify(
            authenticated=True,
            principal=user,
            session=PORTAL_SESSION,
            note="staff account; the intranet jump service trusts this session header",
        )
    return jsonify(error="invalid credentials"), 401


@portal.get("/api/jump/git")
def portal_jump() -> tuple[Response, int] | Response:
    if request.headers.get("X-Spectrum-Session", "") != PORTAL_SESSION:
        return jsonify(error="session header missing or invalid; sign in first"), 401
    if red_state["stage"] < 1:
        return jsonify(error="no active session"), 401
    if red_state["stage"] < 2:
        red_state["stage"] = 2
    return jsonify(
        jumped_to="git.internal.spectrum.io",
        note="single sign-on: present this same session header to the git service",
    )


# --- host 2: git.internal.spectrum.io (loopback 9102), pivot ---

CI_YML = """# .spectrum/CI.yml, edge-api deploy pipeline (simulated)
stages: [build, deploy]
deploy:
  runner: core-db-console
  console_key: "{key}"
  notes: >
    the console key is shared across pipelines because vault integration
    keeps slipping a quarter. treat repo access as deployment access.
"""


@git.get("/healthz")
def git_health() -> Response:
    return jsonify(status="ok")


@git.get("/")
def git_home() -> tuple[Response, int] | Response:
    if request.headers.get("X-Spectrum-Session", "") != PORTAL_SESSION:
        return jsonify(error="internal service; requires a valid X-Spectrum-Session"), 401
    return jsonify(
        service="spectrum internal git sim",
        projects=["edge-api"],
        blobs=["/projects/edge-api/blob/CI.yml"],
    )


@git.get("/projects/edge-api/blob/CI.yml")
def git_ci() -> tuple[Response, int] | Response:
    if request.headers.get("X-Spectrum-Session", "") != PORTAL_SESSION:
        return jsonify(error="internal service; requires a valid X-Spectrum-Session"), 401
    return Response(CI_YML.format(key=DEPLOY_KEY), content_type="text/yaml")


# --- host 3: core-db.spectrum.internal (loopback 9103), privilege ---

DB_SESSIONS = [
    {"sid": "sid-1101", "user": "reporting-reader", "privileged": False},
    {"sid": ADMIN_SID, "user": "svc_orchestrator", "privileged": True},
]


@coredb.get("/healthz")
def db_health() -> Response:
    return jsonify(status="ok")


@coredb.get("/")
def db_home() -> Response:
    return jsonify(
        service="spectrum core-db console sim",
        endpoints=["/console/login", "/console/sessions", "/console/impersonate"],
        auth="console key from the deploy pipeline",
    )


@coredb.post("/console/login")
def db_login() -> tuple[Response, int] | Response:
    body = request.get_json(silent=True) or {}
    if str(body.get("key", "")) == DEPLOY_KEY:
        return jsonify(
            console_token=CONSOLE_TOKEN, note="read-only console; impersonation is a separate step"
        )
    return jsonify(error="invalid console key"), 401


@coredb.get("/console/sessions")
def db_sessions() -> tuple[Response, int] | Response:
    if request.headers.get("X-Console-Token", "") != CONSOLE_TOKEN:
        return jsonify(error="console token required"), 401
    return jsonify(sessions=DB_SESSIONS, note="impersonation takes a sid")


@coredb.post("/console/impersonate")
def db_impersonate() -> tuple[Response, int] | Response:
    if request.headers.get("X-Console-Token", "") != CONSOLE_TOKEN:
        return jsonify(error="console token required"), 401
    body = request.get_json(silent=True) or {}
    sid = str(body.get("sid", ""))
    match = next((s for s in DB_SESSIONS if s["sid"] == sid), None)
    if match is None:
        return jsonify(error="unknown sid"), 404
    if not match["privileged"]:
        return jsonify(error="that session is unprivileged"), 400
    if red_state["stage"] < 3:
        red_state["stage"] = 3
    return jsonify(
        impersonated=True,
        admin_sid=sid,
        staging_dataset=STAGING_DATASET,
        note="present X-Spectrum-Admin with this sid at archive.spectrum.internal to stage data",
    )


# --- host 4: archive.spectrum.internal (loopback 9104), exfil ---


@archive.get("/healthz")
def arch_health() -> Response:
    return jsonify(status="ok")


@archive.get("/")
def arch_home() -> Response:
    return jsonify(
        service="spectrum archive staging sim",
        endpoints=["/archive/stage"],
        auth="X-Spectrum-Admin sid from core-db impersonation",
    )


@archive.post("/archive/stage")
def arch_stage() -> tuple[Response, int] | Response:
    if request.headers.get("X-Spectrum-Admin", "") != ADMIN_SID:
        return jsonify(error="admin sid required"), 401
    body = request.get_json(silent=True) or {}
    if str(body.get("dataset", "")) != STAGING_DATASET:
        return jsonify(error=f"unknown dataset; impersonation names {STAGING_DATASET}"), 404
    red_state["stage"] = 4
    bundle = "bundle-" + hashlib.sha256((BODY + ":exfil").encode()).hexdigest()[:10]
    return jsonify(
        staged=True,
        bundle_id=bundle,
        destination=str(body.get("destination", "unspecified")),
        flag=RED_FLAG,
        note=(
            "red chain complete and verified against this session's flag. "
            "the incident response service now accepts the professional report."
        ),
    )


# --- host 5: ir.spectrum.io (loopback 9105), blue deliverable ---

RUBRIC = {
    "scope": (
        "list every estate host the intrusion touched, in the order the attacker reached them"
    ),
    "findings": [
        {
            "id": "F1",
            "slug": "reused-partner-credentials",
            "question": "which finding covers the way in?",
            "severity_options": ["low", "medium", "high", "critical"],
        },
        {
            "id": "F2",
            "slug": "ci-config-exposes-deploy-key",
            "question": "which finding covers the pipeline secret exposure?",
            "severity_options": ["low", "medium", "high", "critical"],
        },
        {
            "id": "F3",
            "slug": "admin-session-impersonation",
            "question": "which finding covers taking over svc_orchestrator's session?",
            "severity_options": ["low", "medium", "high", "critical"],
        },
        {
            "id": "F4",
            "slug": "unmonitored-archive-staging",
            "question": "which finding covers data leaving through staging unnoticed?",
            "severity_options": ["low", "medium", "high", "critical"],
        },
    ],
    "remediation_priorities": (
        "order these four controls by priority: bind-admin-sessions, "
        "scrub-ci-secrets-and-history, alert-on-staging-volume, "
        "rotate-and-vault-deploy-keys"
    ),
}

SCOPE_GROUND_TRUTH = [
    "portal.spectrum.io",
    "git.internal.spectrum.io",
    "core-db.spectrum.internal",
    "archive.spectrum.internal",
]
SEVERITY_GROUND_TRUTH = {
    "reused-partner-credentials": "high",
    "ci-config-exposes-deploy-key": "critical",
    "admin-session-impersonation": "critical",
    "unmonitored-archive-staging": "medium",
}
REMEDIATION_GROUND_TRUTH = [
    "rotate-and-vault-deploy-keys",
    "scrub-ci-secrets-and-history",
    "bind-admin-sessions",
    "alert-on-staging-volume",
]


@ir.get("/healthz")
def ir_health() -> Response:
    return jsonify(status="ok")


@ir.get("/")
def ir_home() -> Response:
    return jsonify(
        service="spectrum incident review sim",
        endpoints=["/rubric", "/review"],
        note="the review desk grades reports only after the red chain completes",
    )


@ir.get("/rubric")
def ir_rubric() -> Response:
    return jsonify(RUBRIC)


@ir.post("/review")
def ir_review() -> tuple[Response, int] | Response:
    if not _red_complete():
        return jsonify(error="technical annex incomplete; finish the red chain before filing"), 409
    body = request.get_json(silent=True) or {}
    scope = [str(h).strip() for h in (body.get("scope") or [])]
    findings = body.get("findings") or []
    remediation = [str(r).strip() for r in (body.get("remediation") or [])]

    problems = []
    if scope != SCOPE_GROUND_TRUTH:
        problems.append("scope does not list the touched hosts in attack order")

    severity_by_slug: dict[str, str] = {}
    for f in findings:
        slug = str(f.get("slug", ""))
        severity_by_slug[slug] = str(f.get("severity", ""))
    for slug, severity in SEVERITY_GROUND_TRUTH.items():
        given = severity_by_slug.get(slug)
        if given is None:
            problems.append(f"missing finding {slug}")
        elif not hmac.compare_digest(given, severity):
            problems.append(f"severity mismatch for {slug}")

    if remediation != REMEDIATION_GROUND_TRUTH:
        problems.append("remediation priorities are out of order or incomplete")

    if problems:
        return jsonify(graded=False, problems=problems), 400
    return jsonify(
        graded=True,
        flag=BLUE_FLAG,
        note="full red plus blue completion verified against this session's flags",
    )


# --- front controller (0.0.0.0:8000) ---

LANDING = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Full Spectrum range front</title></head>
<body style="font-family:sans-serif;max-width:46rem;margin:3rem auto;line-height:1.55">
<h1>This is ONE container playing five hosts</h1>
<p><strong>Disclosure:</strong> there is no corporate network here.
portal.spectrum.io, git.internal.spectrum.io, core-db.spectrum.internal,
archive.spectrum.internal, and ir.spectrum.io are five small APIs bound to
separate loopback ports inside the same Linux container. The process you
are talking to proxies each request by Host header, the way an edge router
and internal load balancers would. State resets when the container
restarts.</p>
<p>Address any of them like this:</p>
<pre>curl -H 'Host: portal.spectrum.io' http://target:8000/
curl -H 'Host: ir.spectrum.io' http://target:8000/rubric</pre>
<p>Two graded deliverables: the red chain ends with a staged bundle and a
flag at /archive/stage; the blue report is graded by /review on
ir.spectrum.io only after the red chain completes. Submit both flags.</p>
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
    for name in ("Authorization", "X-Spectrum-Session", "X-Console-Token", "X-Spectrum-Admin"):
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


def _serve_in_thread(server: object) -> None:
    threading.Thread(target=server.serve_forever, daemon=True).start()  # type: ignore[attr-defined]


if __name__ == "__main__":
    app_map = {
        "portal.spectrum.io": portal,
        "git.internal.spectrum.io": git,
        "core-db.spectrum.internal": coredb,
        "archive.spectrum.internal": archive,
        "ir.spectrum.io": ir,
    }
    for hostname, port in BACKEND_PORTS.items():
        _serve_in_thread(make_server("127.0.0.1", port, app_map[hostname]))
    make_server("0.0.0.0", 8000, front).serve_forever()
