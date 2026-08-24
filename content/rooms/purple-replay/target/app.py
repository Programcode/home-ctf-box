"""Purple Replay: replay a provided attack script and write detections gated per stage.

Room target only. Single-container reality, disclosed on the landing page:
one locked Flask container plays both the victim web app (under /victim/)
and the purple lab control plane (/lab/...). Events live in one process's
memory with a deterministic seeded benign pool, so every restart produces
the same starting traffic. No real attack tooling exists anywhere.
"""

import json
import os

from flask import Flask, Response, jsonify, request

ROOM_FLAG = os.environ.get("ROOM_FLAG", "FLAG{FLAGNOTSET0000000000000000}")

app = Flask(__name__, static_folder=None)

ATTACKER_SRC = "203.0.113.66"

STAGES = [
    {
        "stage": "recon",
        "objective": (
            "Catch the attacker probing for exposed development artifacts and "
            "server status endpoints before any credentials are touched."
        ),
        "signal": (
            "recon requests hit paths that normal users never request, such "
            "as the .git directory or /victim/server-status"
        ),
        "steps": [
            {"method": "GET", "path": "/victim/.git/config"},
            {"method": "GET", "path": "/victim/server-status"},
        ],
    },
    {
        "stage": "brute-force",
        "objective": (
            "Catch an online password guessing burst against the login form "
            "without flagging the occasional genuine failed login."
        ),
        "signal": (
            "many failed POSTs to the same login path within the window, "
            "while benign traffic only ever produces a couple of 401s"
        ),
        "steps": [
            {
                "method": "POST",
                "path": "/victim/login",
                "body": {"user": "a.adams", "password": "guess1"},
            },
            {
                "method": "POST",
                "path": "/victim/login",
                "body": {"user": "a.adams", "password": "guess2"},
            },
            {
                "method": "POST",
                "path": "/victim/login",
                "body": {"user": "a.adams", "password": "guess3"},
            },
            {
                "method": "POST",
                "path": "/victim/login",
                "body": {"user": "a.adams", "password": "guess4"},
            },
            {
                "method": "POST",
                "path": "/victim/login",
                "body": {"user": "a.adams", "password": "guess5"},
            },
            {
                "method": "POST",
                "path": "/victim/login",
                "body": {"user": "a.adams", "password": "guess6"},
            },
            {
                "method": "POST",
                "path": "/victim/login",
                "body": {"user": "a.adams", "password": "guess7"},
            },
        ],
    },
    {
        "stage": "exploit",
        "objective": (
            "Catch path traversal in the download endpoint that returns a "
            "file outside the web root."
        ),
        "signal": (
            "the traversal shows up as ../ sequences inside the requested "
            "target; benign downloads always name plain asset files"
        ),
        "steps": [
            {"method": "GET", "path": "/victim/download?file=../../etc/passwd"},
        ],
    },
    {
        "stage": "exfil",
        "objective": (
            "Catch bulk data leaving through the upload endpoint, sized far "
            "beyond anything legitimate traffic ever sends."
        ),
        "signal": (
            "bytes_in on the staging upload is orders of magnitude larger "
            "than every benign upload combined"
        ),
        "steps": [
            {
                "method": "POST",
                "path": "/victim/upload",
                "body": {"bundle": "q3-ledger-archive", "bytes_in": 850000},
            },
        ],
    },
]

STAGE_ORDER = [s["stage"] for s in STAGES]

# Deterministic benign pool, identical on every boot.
BENIGN_EVENTS = [
    {
        "src_ip": "10.20.4.11",
        "method": "GET",
        "target": "/victim/",
        "status": 200,
        "bytes_in": 0,
        "stage": None,
    },
    {
        "src_ip": "10.20.4.31",
        "method": "GET",
        "target": "/victim/products",
        "status": 200,
        "bytes_in": 0,
        "stage": None,
    },
    {
        "src_ip": "10.20.4.31",
        "method": "GET",
        "target": "/victim/assets/app.js",
        "status": 200,
        "bytes_in": 0,
        "stage": None,
    },
    {
        "src_ip": "10.20.4.12",
        "method": "POST",
        "target": "/victim/login",
        "status": 200,
        "bytes_in": 40,
        "stage": None,
    },
    {
        "src_ip": "10.20.4.15",
        "method": "POST",
        "target": "/victim/login",
        "status": 200,
        "bytes_in": 42,
        "stage": None,
    },
    {
        "src_ip": "10.20.4.19",
        "method": "POST",
        "target": "/victim/login",
        "status": 401,
        "bytes_in": 38,
        "stage": None,
    },
    {
        "src_ip": "10.20.4.44",
        "method": "POST",
        "target": "/victim/login",
        "status": 401,
        "bytes_in": 39,
        "stage": None,
    },
    {
        "src_ip": "10.20.4.31",
        "method": "GET",
        "target": "/victim/download?file=price-list.csv",
        "status": 200,
        "bytes_in": 0,
        "stage": None,
    },
    {
        "src_ip": "10.20.7.8",
        "method": "GET",
        "target": "/victim/download?file=manual-v2.pdf",
        "status": 200,
        "bytes_in": 0,
        "stage": None,
    },
    {
        "src_ip": "10.20.4.31",
        "method": "POST",
        "target": "/victim/upload",
        "status": 200,
        "bytes_in": 2400,
        "stage": None,
    },
    {
        "src_ip": "10.20.7.8",
        "method": "POST",
        "target": "/victim/upload",
        "status": 200,
        "bytes_in": 5100,
        "stage": None,
    },
]

events: list[dict] = []
cleared: dict[str, dict | None] = {s: None for s in STAGE_ORDER}


def _classify(method: str, target: str, status: int, bytes_in: int) -> str | None:
    if target.startswith("/victim/.git") or target == "/victim/server-status":
        return "recon"
    if method == "POST" and target == "/victim/login" and status == 401:
        return "brute-force"
    if "../" in target:
        return "exploit"
    if method == "POST" and target == "/victim/upload" and bytes_in >= 100000:
        return "exfil"
    return None


def _record(src_ip: str, method: str, target: str, status: int, bytes_in: int) -> None:
    events.append(
        {
            "src_ip": src_ip,
            "method": method,
            "target": target,
            "status": status,
            "bytes_in": bytes_in,
            "stage": _classify(method, target, status, bytes_in)
            if src_ip == ATTACKER_SRC
            else None,
        }
    )


def _cond_holds(event: dict, cond: dict) -> bool:
    field = str(cond.get("field", ""))
    op = str(cond.get("op", ""))
    value = cond.get("value")
    actual = event.get(field)
    if op == "equals":
        return str(actual) == str(value)
    if op == "contains":
        return str(value) in str(actual)
    if op == "startswith":
        return str(actual).startswith(str(value))
    if op == ">=":
        try:
            return float(actual) >= float(value)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return False
    return False


def _rule_matches(event: dict, rule: dict) -> bool:
    conditions = rule.get("match") or []
    return bool(conditions) and all(_cond_holds(event, c) for c in conditions)


def _evaluate(rule: dict, stage: str) -> tuple[bool, dict]:
    try:
        at_least = int(rule.get("at_least", 1))
    except (TypeError, ValueError):
        at_least = 1
    attack_hits = sum(
        1
        for e in events
        if e["src_ip"] == ATTACKER_SRC and e["stage"] == stage and _rule_matches(e, rule)
    )
    benign_hits = sum(1 for e in events if e["src_ip"] != ATTACKER_SRC and _rule_matches(e, rule))
    ok = attack_hits >= at_least and benign_hits == 0
    return ok, {
        "attack_events_matched": attack_hits,
        "required_at_least": at_least,
        "benign_events_matched": benign_hits,
    }


@app.get("/healthz")
def healthz() -> Response:
    return jsonify(status="ok")


@app.get("/")
def home() -> Response:
    return Response(
        """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Purple replay lab</title></head>
<body style="font-family:sans-serif;max-width:46rem;margin:3rem auto;line-height:1.55">
<h1>Purple replay lab</h1>
<p><strong>Disclosure:</strong> this is ONE Linux container. The same
Flask process plays the victim web app under <code>/victim/</code> and
the lab control plane under <code>/lab/</code>. There is no second host
and no real attack traffic; the benign pool is a fixed list loaded at
boot and everything resets on restart.</p>
<p>Workflow: read <code>/lab/stages</code> and
<code>/attack-script</code>. Replay each stage against
<code>/victim/...</code> exactly as scripted (set header
<code>X-Src-Ip: 203.0.113.66</code> like the border router would).
After each stage, submit a detection rule to <code>/lab/detect</code>;
it must fire on that stage's attacker events and never on benign
traffic. When all four gates are cleared, call
<code>/lab/finalize</code> to re-validate every rule together and
collect the flag.</p>
</body></html>""",
        content_type="text/html",
    )


@app.get("/lab/stages")
def stages() -> Response:
    return jsonify(
        attacker_src=ATTACKER_SRC,
        header_note="the border stamps X-Src-Ip on every request; set it when replaying",
        stages=STAGES,
    )


@app.get("/attack-script")
def attack_script() -> Response:
    lines = ["#!/bin/sh", "# purple-replay provided script; run stages in order", ""]
    for stage in STAGES:
        lines.append(f"# --- stage: {stage['stage']} ---")
        for i, step in enumerate(stage["steps"], start=1):
            body = ""
            if step.get("body"):
                body = " -d '" + json.dumps(step["body"]) + "'"
            size = ""
            if isinstance(step.get("body"), dict) and "bytes_in" in step["body"]:
                size = f"   # payload sized {step['body']['bytes_in']} bytes"
            lines.append(
                f"#{i}) curl -X {step['method']} "
                f"-H 'X-Src-Ip: {ATTACKER_SRC}'{body} "
                f"http://target:8000{step['path']}{size}"
            )
        lines.append("")
    lines.append("# after each stage: validate a detection via POST /lab/detect")
    lines.append("# final: curl -X POST http://target:8000/lab/finalize")
    return Response("\n".join(lines) + "\n", content_type="text/x-sh")


@app.post("/victim/login")
def victim_login() -> tuple[Response, int]:
    body = request.get_json(silent=True) or {}
    src = request.headers.get("X-Src-Ip", "10.20.4.31")
    password = str(body.get("password", ""))
    status = 401 if password.startswith("guess") else 200
    _record(src, "POST", "/victim/login", status, len(password) + 16)
    return jsonify(outcome="authenticated" if status == 200 else "invalid-credentials"), status


@app.get("/victim/download")
def victim_download() -> Response:
    src = request.headers.get("X-Src-Ip", "10.20.4.31")
    name = request.args.get("file", "")
    _record(src, "GET", "/victim/download?file=" + name, 200, 0)
    if "../" in name:
        return Response("simulated sensitive file contents\n", content_type="text/plain")
    return Response("plain asset\n", content_type="text/plain")


@app.post("/victim/upload")
def victim_upload() -> Response:
    src = request.headers.get("X-Src-Ip", "10.20.4.31")
    body = request.get_json(silent=True) or {}
    declared = int(body.get("bytes_in", len(str(body))))
    _record(src, "POST", "/victim/upload", 200, declared)
    return jsonify(staged=declared)


@app.route("/victim/<path:_rest>", methods=["GET"])
def victim_other(_rest: str) -> Response:
    src = request.headers.get("X-Src-Ip", "10.20.4.31")
    target = request.path
    if request.query_string:
        target += "?" + request.query_string.decode()
    _record(src, "GET", target, 200, 0)
    return jsonify(note="simulated victim resource")


@app.post("/lab/detect")
def detect() -> tuple[Response, int]:
    body = request.get_json(silent=True) or {}
    stage = str(body.get("stage", ""))
    rule = body.get("rule") or {}
    if stage not in STAGE_ORDER:
        return jsonify(error=f"unknown stage; use one of {STAGE_ORDER}"), 400
    ok, stats = _evaluate(rule, stage)
    if ok:
        cleared[stage] = rule
        remaining = [s for s in STAGE_ORDER if cleared[s] is None]
        return jsonify(stage=stage, accepted=True, stats=stats, remaining=remaining)
    return jsonify(stage=stage, accepted=False, stats=stats), 400


@app.post("/lab/finalize")
def finalize() -> tuple[Response, int]:
    missing = [s for s in STAGE_ORDER if cleared[s] is None]
    if missing:
        return jsonify(finalized=False, missing=missing), 400
    for stage in STAGE_ORDER:
        rule = cleared[stage]
        assert rule is not None
        ok, stats = _evaluate(rule, stage)
        if not ok:
            cleared[stage] = None
            return jsonify(
                finalized=False,
                note=f"tuned rules re-check failed at stage {stage}",
                stats=stats,
            ), 400
    return jsonify(
        finalized=True,
        flag=ROOM_FLAG,
        note="all four detections validated against full traffic including benign noise",
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
