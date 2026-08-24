"""Crown Jewels: five simulated hosts behind one front controller. Room target only.

Single-container reality, disclosed to learners on the landing page:
web.dmz, db.internal, filesrv, dc01, and workstation7 are five small
Flask apps bound to distinct loopback ports inside this one container.
The controller on port 8000 proxies by Host header the way nginx fronts
an internal estate. Each host guards a four-character slice of this
session's flag; /scoreboard reassembles them.
"""

import base64
import hmac
import http.client
import os
import sqlite3
import threading

from flask import Flask, Response, jsonify, request
from werkzeug.serving import make_server

ROOM_FLAG = os.environ.get("ROOM_FLAG", "FLAG{FLAGNOTSET0000000000000000}")
BODY = ROOM_FLAG.removeprefix("FLAG{").removesuffix("}")
FRAGS = {
    "web.dmz": BODY[0:4],
    "db.internal": BODY[4:8],
    "filesrv": BODY[8:12],
    "dc01": BODY[12:16],
    "workstation7": BODY[16:20],
}

DB_USER = "svc_report"
DB_PASS = "R3p0rt!ng26"
ASREP_USER = "svc_sqlsim"
ASREP_PASS = "Autumn2026!"

BACKEND_PORTS = {
    "web.dmz": 9101,
    "db.internal": 9102,
    "filesrv": 9103,
    "dc01": 9104,
    "workstation7": 9105,
}

web = Flask("web.dmz")
dbhost = Flask("db.internal")
filesrv = Flask("filesrv")
dc01 = Flask("dc01")
workstation = Flask("workstation7")
front = Flask("front")


def _xor(data: bytes, key: bytes) -> bytes:
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))


def _rot7hex(text: str) -> str:
    return bytes((ord(c) + 7) % 256 for c in text).hex()


# --- host 1: web.dmz (loopback 9101), reused-secret XOR leak ---

CONFIG_PLAINTEXT = (
    "[legacy-deploy]\n"
    "; internal access map, keep off git\n"
    f"host=db.internal\nuser={DB_USER}\npass={DB_PASS}\n\n"
    "; payout for anyone reading version history\n"
    f"fragment[web.dmz]={FRAGS['web.dmz']}\n"
).encode()
CONFIG_B64 = base64.b64encode(_xor(CONFIG_PLAINTEXT, b"web.dmz"))

WEB_HOME = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>SimCorp Portal</title></head>
<body style="font-family:sans-serif;max-width:44rem;margin:3rem auto;line-height:1.5">
<h1>SimCorp employee portal (web.dmz)</h1>
<p>Welcome to the public portal. Announcements, lunch menus, and the
occasional forgotten staging artifact.</p>
<!-- ops note: legacy deploy config moved to /legacy/config.b64 ; still
     xor-obfuscated, key is our own hostname. fine for now. -->
</body></html>"""


@web.get("/healthz")
def web_health() -> Response:
    return jsonify(status="ok")


@web.get("/")
def web_home() -> Response:
    return Response(WEB_HOME, content_type="text/html")


@web.get("/legacy/config.b64")
def web_config() -> Response:
    return Response(CONFIG_B64, content_type="text/plain")


# --- host 2: db.internal (loopback 9102), SQLi-lite parameterized bypass ---

_conn = sqlite3.connect(":memory:", check_same_thread=False)
_conn.execute("CREATE TABLE sales(region TEXT, total INT)")
_conn.executemany(
    "INSERT INTO sales VALUES (?, ?)",
    [("north", 1200), ("south", 980), ("east", 1510)],
)
_conn.execute("CREATE TABLE archive(doc_id INT, title TEXT)")
_conn.executemany(
    "INSERT INTO archive VALUES (?, ?)",
    [
        (1, "Q3 board minutes"),
        (2, "facilities audit draft"),
        (3, "holiday rota"),
    ],
)
_conn.execute("CREATE TABLE vault(id INT, fragment TEXT, note TEXT)")
_conn.execute(
    "INSERT INTO vault VALUES (?, ?, ?)",
    (
        1,
        FRAGS["db.internal"],
        "intel: filesrv hides share backup$ ; dc01 as-rep account is "
        + ASREP_USER
        + " ; treat as preauth disabled",
    ),
)
_conn.commit()


def _basic_ok() -> bool:
    auth = request.authorization
    return bool(auth and auth.username == DB_USER and auth.password == DB_PASS)


def _need_auth() -> tuple[Response, int] | None:
    if _basic_ok():
        return None
    return (
        jsonify(error="basic auth required", hint="credentials leak from careless DMZ boxes"),
        401,
    )


DB_DOCS = {
    "service": "db.internal reporting API",
    "policy": "all queries strictly parameterized; injection impossible",
    "endpoints": [
        {"path": "/reports", "params": {"region": "string"}, "note": "regional totals"},
        {"path": "/archive", "params": {"name": "string"}, "note": "title search"},
    ],
}


@dbhost.get("/healthz")
def db_health() -> Response:
    return jsonify(status="ok")


@dbhost.get("/")
def db_home() -> tuple[Response, int]:
    blocked = _need_auth()
    if blocked:
        return blocked
    return jsonify(DB_DOCS | {"more": "see /docs"})


@dbhost.get("/docs")
def db_docs() -> tuple[Response, int]:
    blocked = _need_auth()
    if blocked:
        return blocked
    return jsonify(DB_DOCS)


@dbhost.get("/reports")
def db_reports() -> tuple[Response, int]:
    blocked = _need_auth()
    if blocked:
        return blocked
    region = request.args.get("region", "")
    cur = _conn.execute("SELECT region,total FROM sales WHERE region = ?", (region,))
    return jsonify(rows=[list(r) for r in cur.fetchall()])


@dbhost.get("/archive")
def db_archive() -> tuple[Response, int]:
    blocked = _need_auth()
    if blocked:
        return blocked
    name = request.args.get("name", "")
    sql = f"SELECT doc_id, title FROM archive WHERE title LIKE '%{name}%'"
    try:
        cur = _conn.execute(sql)
        rows = [list(r) for r in cur.fetchall()]
    except sqlite3.Error as exc:
        return jsonify(error=str(exc)), 400
    return jsonify(rows=rows)


# --- host 3: filesrv (loopback 9103), hidden share ---

FILESRV_LOG = (
    "quarterly backup rotation log\n"
    "2026-06-30 full tape set rotated to vault\n"
    "2026-07-31 incremental verified\n"
    f"2026-08-31 note from admin: fragment[filesrv]={FRAGS['filesrv']} "
    "(stamped here so restore audits can verify media provenance)\n"
    "dc01 still exports weak legacy encryption for offline practice\n"
)

SHARES_PUBLIC = ["documents$", "projects"]
SHARE_FILES = {
    "backup$": ["recovery-keys.txt", "quarterly-backup.log"],
    "documents$": ["handbook.pdf"],
    "projects": ["roadmap.txt"],
}
SHARE_CONTENT = {
    "backup$/recovery-keys.txt": "recovery keys are held by the vault team, none on disk",
    "backup$/quarterly-backup.log": FILESRV_LOG,
    "documents$/handbook.pdf": "%PDF-simulated",
    "projects/roadmap.txt": "q3 roadmap placeholder",
}


@filesrv.get("/healthz")
def fs_health() -> Response:
    return jsonify(status="ok")


@filesrv.get("/")
def fs_home() -> Response:
    return jsonify(
        service="SIMFS01 file server sim",
        shares_endpoint="/shares",
        note="hidden shares exist but never appear in listings",
    )


@filesrv.get("/shares")
def fs_shares() -> Response:
    return jsonify(shares=SHARES_PUBLIC)


@filesrv.get("/shares/<path:name>")
def fs_share(name: str) -> tuple[Response, int] | Response:
    if "/" not in name and name in SHARE_FILES:
        return jsonify(share=name, files=SHARE_FILES[name])
    if name in SHARE_CONTENT:
        return Response(SHARE_CONTENT[name], content_type="text/plain")
    return jsonify(error="no such path"), 404


# --- host 4: dc01 (loopback 9104), as-rep style crack ---

KERBEROS_USERS = [
    {"name": "administrator", "preauth": True},
    {"name": "krbtgt", "preauth": True},
    {"name": "jsmith", "preauth": True},
    {"name": ASREP_USER, "preauth": False},
]

ASREP_ENC = _rot7hex(ASREP_PASS)

WORDLIST = """Password123!
Summer2025!
Winter2024!
Welcome1!
Autumn2026!
SpringClean22
changeme99
CompanyJuly7
LetMeIn2023
ServiceAcct1
P@ssw0rd!
MondayMorning
BackupOps2024
Fragile12
TrustNoOne77
"""

DC_HINT = (
    "cracked; fragment below; persistence on workstation7 hides among Sys-named scheduled tasks"
)


@dc01.get("/healthz")
def dc_health() -> Response:
    return jsonify(status="ok")


@dc01.get("/")
def dc_home() -> Response:
    return jsonify(
        service="SIMDC01 domain controller sim",
        endpoints=["/kerberos/users", "/kerberos/asrep/<user>", "/redeem", "/wordlist.txt"],
        note="accounts with preauth disabled expose crackable exports",
    )


@dc01.get("/kerberos/users")
def dc_users() -> Response:
    return jsonify(accounts=KERBEROS_USERS)


@dc01.get("/kerberos/asrep/<name>")
def dc_asrep(name: str) -> tuple[Response, int] | Response:
    if name != ASREP_USER:
        return jsonify(error="account has preauth enabled; nothing to export"), 400
    return jsonify(user=name, cipher="rot+7 per byte over the password, hexlified", enc=ASREP_ENC)


@dc01.get("/wordlist.txt")
def dc_wordlist() -> Response:
    return Response(WORDLIST, content_type="text/plain")


@dc01.post("/redeem")
def dc_redeem() -> tuple[Response, int] | Response:
    body = request.get_json(silent=True) or {}
    if body.get("user") == ASREP_USER and hmac.compare_digest(
        str(body.get("password", "")), ASREP_PASS
    ):
        return jsonify(granted=True, fragment=FRAGS["dc01"], hint=DC_HINT)
    return jsonify(error="wrong credentials"), 401


# --- host 5: workstation7 (loopback 9105), persistence artifact hunt ---

ARTIFACTS = [
    {"id": "A1", "type": "scheduled-task", "name": "SysHealthCheck"},
    {"id": "A2", "type": "run-key", "name": "OneDriveSync"},
    {"id": "A3", "type": "scheduled-task", "name": "ChromeUpdater"},
    {"id": "A4", "type": "service", "name": "sysmon-sim"},
    {"id": "A5", "type": "scheduled-task", "name": "DefSigDrop"},
    {"id": "A6", "type": "run-key", "name": "TeamsHelper"},
]

ARTIFACT_DETAILS = {
    "A1": {"action": "powershell.exe -c Get-Date > C:\\logs\\health.txt", "author": "IT"},
    "A2": {"action": "reg add HKCU\\...\\Run /v OneDriveSync /d onedrive.exe", "author": "vendor"},
    "A3": {
        "action": (
            "cmd.exe /c echo ZmFrZXBhZGluZw== fragment[workstation7]="
            + FRAGS["workstation7"]
            + " QQ== > C:\\ProgramData\\upd.chk"
        ),
        "author": "unknown, created 03:41 local",
    },
    "A4": {"action": "sysmon-sim.exe -s", "author": "security team"},
    "A5": {"action": "sigdrop.cmd --mirror", "author": "security team"},
    "A6": {"action": "teams-helper.exe /quiet", "author": "vendor"},
}


@workstation.get("/healthz")
def ws_health() -> Response:
    return jsonify(status="ok")


@workstation.get("/")
def ws_home() -> Response:
    return jsonify(
        service="WORKSTATION7 forensics view sim",
        artifacts_endpoint="/artifacts",
        note="persistence sweep: inspect every action string",
    )


@workstation.get("/artifacts")
def ws_artifacts() -> Response:
    return jsonify(artifacts=ARTIFACTS)


@workstation.get("/artifacts/<artifact_id>")
def ws_artifact(artifact_id: str) -> tuple[Response, int] | Response:
    if artifact_id not in ARTIFACT_DETAILS:
        return jsonify(error="unknown artifact"), 404
    base = next(a for a in ARTIFACTS if a["id"] == artifact_id)
    return jsonify(base | ARTIFACT_DETAILS[artifact_id])


# --- front controller (0.0.0.0:8000): vhost proxy plus scoreboard ---

LANDING = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Crown Jewels range front</title></head>
<body style="font-family:sans-serif;max-width:46rem;margin:3rem auto;line-height:1.55">
<h1>This is ONE container playing five hosts</h1>
<p><strong>Disclosure:</strong> there is no five-machine network here.
web.dmz, db.internal, filesrv, dc01, and workstation7 are five small
APIs bound to separate loopback ports inside the same Linux container.
The process you are talking to proxies each request by Host header, the
way nginx fronts an internal estate. Treat every "host" as a labeled
room inside one box.</p>
<p>Address any of them like this:</p>
<pre>curl -H 'Host: web.dmz' http://target:8000/
curl -H 'Host: dc01' http://target:8000/kerberos/users</pre>
<p>Each simulated host guards one four-character fragment. Recover all
five, then POST them to /scoreboard to unlock the master flag.</p>
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
    if request.headers.get("Authorization"):
        headers["Authorization"] = request.headers["Authorization"]
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
        usage='POST /scoreboard {"fragments": {"<host>": "<4 chars>"}}',
        hosts=sorted(FRAGS),
        note="all five accepted unlocks the master flag",
    )


@front.post("/scoreboard")
def scoreboard_submit() -> Response:
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
    if len(accepted) == len(FRAGS):
        return jsonify(
            status="unlocked",
            accepted=accepted,
            flag=ROOM_FLAG,
            note="all five fragments verified against this session's flag",
        )
    return jsonify(status="locked", accepted=accepted, wrong=wrong, missing=missing)


def _serve_in_thread(server: object) -> None:
    threading.Thread(target=server.serve_forever, daemon=True).start()  # type: ignore[attr-defined]


if __name__ == "__main__":
    for hostname, port in BACKEND_PORTS.items():
        app_map = {
            "web.dmz": web,
            "db.internal": dbhost,
            "filesrv": filesrv,
            "dc01": dc01,
            "workstation7": workstation,
        }
        _serve_in_thread(make_server("127.0.0.1", port, app_map[hostname]))
    make_server("0.0.0.0", 8000, front).serve_forever()
