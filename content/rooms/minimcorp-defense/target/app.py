"""MinimCorp Defense: blue-team investigation console over the breach estate artifacts.

Room target only. Single-container reality, disclosed on the landing page:
this is one locked Flask container serving synthetic evidence files and a
stateful case API. There is no SIEM, no log shipper, and no corporate
network behind it. The artifacts describe the same three-host MinimCorp
estate the red-team room simulates, frozen into exported logs. State lives
in one process and resets when the container restarts.
"""

import os

from flask import Flask, Response, jsonify, request

ROOM_FLAG = os.environ.get("ROOM_FLAG", "FLAG{FLAGNOTSET0000000000000000}")

app = Flask(__name__, static_folder=None)

CASE = {
    "case_id": "IR-2026-0114",
    "status": "open",
    "brief": (
        "Overnight, an external actor walked the same chain the red team "
        "exercise documents: a stale vpn-edge config backup, reused wiki "
        "service credentials, invoice enumeration in the finance API, and a "
        "forged directory-sim admin token. The estate owners exported the "
        "relevant logs before anything was touched. Reconstruct what "
        "happened, name every affected identity, choose containment that "
        "fixes root causes without destroying evidence, then close the case."
    ),
}

EVIDENCE_INDEX = [
    {
        "artifact": "edge-access.log",
        "source": "vpn-edge.minimcorp.net",
        "note": "web access log from the edge portal, plain text",
    },
    {
        "artifact": "wiki-audit.json",
        "source": "wiki.corp.minimcorp.net",
        "note": "wiki authentication and page-read audit export",
    },
    {
        "artifact": "finance-access.json",
        "source": "finance.minimcorp.net",
        "note": "finance API access export with returned-record ids",
    },
    {
        "artifact": "directory-sso.json",
        "source": "finance.minimcorp.net /sso",
        "note": "directory-sim verification attempts and outcomes",
    },
]

EDGE_LOG = """2026-08-20 02:14:07Z GET /static/vpn.conf.bak 200 src=198.51.100.66
2026-08-20 02:14:09Z GET /healthz 200 src=198.51.100.66
2026-08-20 02:15:40Z GET / 200 src=203.0.113.9
"""

WIKI_AUDIT = {
    "events": [
        {
            "time": "02:21:12Z",
            "kind": "auth",
            "user": "svc_wiki",
            "outcome": "ok",
            "src": "198.51.100.66",
        },
        {"time": "02:26:48Z", "kind": "page-read", "page": "finance-runbook", "user": "svc_wiki"},
        {
            "time": "02:27:31Z",
            "kind": "revisions-read",
            "page": "finance-runbook",
            "user": "svc_wiki",
        },
        {
            "time": "01:58:03Z",
            "kind": "auth",
            "user": "f.okafor",
            "outcome": "ok",
            "src": "10.20.4.11",
        },
    ],
}

FINANCE_ACCESS = {
    "events": [
        {
            "time": "02:38:55Z",
            "kind": "invoice-read",
            "employee_id": 1001,
            "record": "j.novak",
            "key_prefix": "fin-api-key-7788",
        },
        {
            "time": "02:39:02Z",
            "kind": "invoice-read",
            "employee_id": 1013,
            "record": "e.szabo",
            "key_prefix": "fin-api-key-7788",
        },
    ],
}

DIRECTORY_SSO = {
    "events": [
        {
            "time": "03:05:19Z",
            "kind": "sso-verify",
            "user": "a.adams",
            "role": "estate-admin",
            "outcome": "token-issued",
        },
        {
            "time": "03:06:02Z",
            "kind": "scoreboard-note",
            "note": "admin token presented to estate services by 198.51.100.66",
        },
    ],
}

STAGE_VOCABULARY = ["config-exposure", "credential-reuse", "data-enumeration", "privilege-forgery"]
TIMELINE_GROUND_TRUTH = [
    {"time": "02:14", "event": "config-exposure"},
    {"time": "02:21", "event": "credential-reuse"},
    {"time": "02:38", "event": "data-enumeration"},
    {"time": "03:05", "event": "privilege-forgery"},
]
AFFECTED_GROUND_TRUTH = sorted(["svc_wiki", "j.novak", "e.szabo", "a.adams"])

PLAYBOOK = {
    "timeline_rule": (
        "Each attack stage maps to exactly one event slug from the stage "
        "vocabulary. Use the minute precision timestamps (HH:MM, UTC) of "
        "the first event of each stage as recorded in the exports."
    ),
    "affected_rule": (
        "An identity is affected when the attacker authenticated as it, "
        "impersonated it, or the estate returned that identity's restricted "
        "records to the attacker. Mentioned colleagues whose records were "
        "never returned do not count."
    ),
    "containment_rule": (
        "Containment must address every root cause the chain exposed, must "
        "not destroy evidence, and must not take healthy services offline. "
        "Choose actions only from the option list; the full correct set is "
        "required, no extras."
    ),
    "containment_options": [
        {
            "slug": "purge-stale-vpn-backups",
            "effect": "removes the leaked rollback snapshot from the edge",
        },
        {
            "slug": "rotate-wiki-service-credentials",
            "effect": "invalidates the reused svc_wiki secret",
        },
        {
            "slug": "revoke-fin-api-key",
            "effect": "kills the static integration key printed in the runbook",
        },
        {
            "slug": "retire-legacy-sso-signing",
            "effect": "replaces the unrotated shared signing scheme",
        },
        {
            "slug": "add-per-record-authorization",
            "effect": "closes the IDOR in the invoice API",
        },
        {
            "slug": "power-off-vpn-edge",
            "effect": "takes remote access down for the whole company",
        },
        {
            "slug": "delete-finance-audit-logs",
            "effect": "destroys the evidence this case depends on",
        },
        {
            "slug": "rotate-domain-admin-password-only",
            "effect": "leaves every other root cause open",
        },
    ],
}

state = {"timeline_ok": False, "accounts_ok": False, "contain_ok": False}


@app.get("/healthz")
def healthz() -> Response:
    return jsonify(status="ok")


@app.get("/")
def home() -> Response:
    return Response(
        """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>MinimCorp IR console</title></head>
<body style="font-family:sans-serif;max-width:46rem;margin:3rem auto;line-height:1.55">
<h1>MinimCorp incident response console</h1>
<p><strong>Disclosure:</strong> this is ONE Linux container. There is no
SIEM cluster, no log shipper, and no corporate network here. A single
Flask app serves synthetic evidence exports shaped like real logs plus a
small stateful case API. The artifacts freeze the same MinimCorp estate
the red-team room simulates. Case state resets when the container
restarts.</p>
<p>Workflow: read <code>/case</code> and <code>/evidence</code>, submit
<code>/timeline</code>, <code>/accounts</code>, and <code>/contain</code>,
then call <code>/close-case</code>. The console grades each stage and
tells you which are still wrong.</p>
</body></html>""",
        content_type="text/html",
    )


@app.get("/case")
def case() -> Response:
    return jsonify(CASE)


@app.get("/evidence")
def evidence() -> Response:
    return jsonify(index=EVIDENCE_INDEX, endpoints=["/evidence/<artifact>"])


@app.get("/evidence/edge-access.log")
def ev_edge() -> Response:
    return Response(EDGE_LOG, content_type="text/plain")


@app.get("/evidence/wiki-audit.json")
def ev_wiki() -> Response:
    return jsonify(WIKI_AUDIT)


@app.get("/evidence/finance-access.json")
def ev_finance() -> Response:
    return jsonify(FINANCE_ACCESS)


@app.get("/evidence/directory-sso.json")
def ev_sso() -> Response:
    return jsonify(DIRECTORY_SSO)


@app.get("/playbook")
def playbook() -> Response:
    return jsonify(PLAYBOOK)


def _stage_status() -> dict:
    return {k: v for k, v in state.items()}


@app.post("/timeline")
def timeline() -> tuple[Response, int] | Response:
    body = request.get_json(silent=True) or {}
    steps = body.get("steps") or []
    normalized = [
        {"time": str(s.get("time", "")).strip(), "event": str(s.get("event", "")).strip()}
        for s in steps
    ]
    if normalized == TIMELINE_GROUND_TRUTH:
        state["timeline_ok"] = True
        return jsonify(stage="timeline", accepted=True, status=_stage_status())
    unknown = [s["event"] for s in normalized if s["event"] not in STAGE_VOCABULARY]
    return jsonify(
        stage="timeline",
        accepted=False,
        unknown_events=unknown,
        expected_count=len(TIMELINE_GROUND_TRUTH),
        received_count=len(normalized),
        hint="four stages, vocabulary slugs only, minute times from each stage's first event",
    ), 400


@app.post("/accounts")
def accounts() -> tuple[Response, int] | Response:
    body = request.get_json(silent=True) or {}
    given = sorted({str(a).strip() for a in (body.get("affected") or [])})
    if given == AFFECTED_GROUND_TRUTH:
        state["accounts_ok"] = True
        return jsonify(stage="accounts", accepted=True, status=_stage_status())
    return jsonify(
        stage="accounts",
        accepted=False,
        submitted=given,
        count=len(given),
        hint="apply the affected_rule to every event across all four exports",
    ), 400


@app.post("/contain")
def contain() -> tuple[Response, int] | Response:
    body = request.get_json(silent=True) or {}
    given = sorted({str(a).strip() for a in (body.get("actions") or [])})
    correct = sorted(
        o["slug"]
        for o in PLAYBOOK["containment_options"]
        if o["slug"]
        in {
            "purge-stale-vpn-backups",
            "rotate-wiki-service-credentials",
            "revoke-fin-api-key",
            "retire-legacy-sso-signing",
            "add-per-record-authorization",
        }
    )
    if given == correct:
        state["contain_ok"] = True
        return jsonify(stage="contain", accepted=True, status=_stage_status())
    invalid = [a for a in given if a not in {o["slug"] for o in PLAYBOOK["containment_options"]}]
    return jsonify(
        stage="contain",
        accepted=False,
        invalid_slugs=invalid,
        submitted_count=len(given),
        hint="every root cause covered, nothing destructive, nothing overbroad",
    ), 400


@app.post("/close-case")
def close_case() -> tuple[Response, int] | Response:
    if all(state.values()):
        return jsonify(
            closed=True,
            flag=ROOM_FLAG,
            note="timeline, accounts, and containment verified against this session's flag",
        )
    outstanding = [k for k, v in state.items() if not v]
    return jsonify(closed=False, outstanding=outstanding), 400


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
