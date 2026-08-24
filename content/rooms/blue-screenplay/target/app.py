"""evtx-sim investigation target: exported JSON channels plus /report. Room only."""

import json
import os

from flask import Flask, Response, jsonify, request

app = Flask(__name__)

ROOM_FLAG = os.environ.get("ROOM_FLAG", "FLAG{FLAGNOTSET0000000000000000}")

D = "2026-08-19T"

SECURITY_EVENTS = [
    # Brute force from outside, then the success that ended it.
    {
        "channel": "Security",
        "event_id": "4625-sim",
        "time": D + "03:10:11Z",
        "host": "WIN-SIM01",
        "account": "svc_backups",
        "source_ip": "198.51.100.23",
        "result": "failed",
    },
    {
        "channel": "Security",
        "event_id": "4625-sim",
        "time": D + "03:10:44Z",
        "host": "WIN-SIM01",
        "account": "svc_backups",
        "source_ip": "198.51.100.23",
        "result": "failed",
    },
    {
        "channel": "Security",
        "event_id": "4625-sim",
        "time": D + "03:11:20Z",
        "host": "WIN-SIM01",
        "account": "svc_backups",
        "source_ip": "198.51.100.23",
        "result": "failed",
    },
    {
        "channel": "Security",
        "event_id": "4625-sim",
        "time": D + "03:12:02Z",
        "host": "WIN-SIM01",
        "account": "svc_backups",
        "source_ip": "198.51.100.23",
        "result": "failed",
    },
    {
        "channel": "Security",
        "event_id": "4625-sim",
        "time": D + "03:12:39Z",
        "host": "WIN-SIM01",
        "account": "svc_backups",
        "source_ip": "198.51.100.23",
        "result": "failed",
    },
    {
        "channel": "Security",
        "event_id": "4625-sim",
        "time": D + "03:13:15Z",
        "host": "WIN-SIM01",
        "account": "svc_backups",
        "source_ip": "198.51.100.23",
        "result": "failed",
    },
    {
        "channel": "Security",
        "event_id": "4625-sim",
        "time": D + "03:14:01Z",
        "host": "WIN-SIM01",
        "account": "svc_backups",
        "source_ip": "198.51.100.23",
        "result": "failed",
    },
    {
        "channel": "Security",
        "event_id": "4624-sim",
        "time": D + "03:16:27Z",
        "host": "WIN-SIM01",
        "account": "svc_backups",
        "source_ip": "198.51.100.23",
        "logon_type": "Network",
        "result": "success",
    },
    # Lateral movement rides the first victim host.
    {
        "channel": "Security",
        "event_id": "4624-sim",
        "time": D + "03:58:12Z",
        "host": "WIN-SIM02",
        "account": "svc_backups",
        "source_ip": "10.20.0.41",
        "logon_type": "Network",
        "result": "success",
    },
    {
        "channel": "Security",
        "event_id": "4624-sim",
        "time": D + "04:01:48Z",
        "host": "WIN-SIM03",
        "account": "svc_backups",
        "source_ip": "10.20.0.41",
        "logon_type": "Network",
        "result": "success",
    },
    # Business-as-usual noise for contrast.
    {
        "channel": "Security",
        "event_id": "4624-sim",
        "time": D + "02:00:05Z",
        "host": "WIN-SIM01",
        "account": "svc_sql",
        "source_ip": "10.20.0.52",
        "logon_type": "Service",
        "result": "success",
    },
    {
        "channel": "Security",
        "event_id": "4624-sim",
        "time": D + "08:02:19Z",
        "host": "WIN-SIM01",
        "account": "jsmith",
        "source_ip": "10.20.0.9",
        "logon_type": "Interactive",
        "result": "success",
    },
    {
        "channel": "Security",
        "event_id": "4624-sim",
        "time": D + "08:05:41Z",
        "host": "WIN-SIM01",
        "account": "alopez",
        "source_ip": "10.20.0.9",
        "logon_type": "Interactive",
        "result": "success",
    },
    {
        "channel": "Security",
        "event_id": "4624-sim",
        "time": D + "08:40:03Z",
        "host": "WIN-SIM02",
        "account": "jsmith",
        "source_ip": "10.20.0.9",
        "logon_type": "RemoteInteractive",
        "result": "success",
    },
    {
        "channel": "Security",
        "event_id": "4625-sim",
        "time": D + "11:30:52Z",
        "host": "WIN-SIM01",
        "account": "jsmith",
        "source_ip": "10.20.0.9",
        "result": "failed",
    },
    {
        "channel": "Security",
        "event_id": "4624-sim",
        "time": D + "09:00:31Z",
        "host": "WIN-SIM03",
        "account": "alopez",
        "source_ip": "10.20.0.9",
        "logon_type": "RemoteInteractive",
        "result": "success",
    },
]

SYSTEM_EVENTS = [
    {
        "channel": "System",
        "event_id": "7031-sim",
        "time": D + "04:02:07Z",
        "host": "WIN-SIM01",
        "service": "SimDefenderAV",
        "message": "The SimDefenderAV service terminated unexpectedly.",
    },
    {
        "channel": "System",
        "event_id": "7031-sim",
        "time": D + "04:19:33Z",
        "host": "WIN-SIM01",
        "service": "BackupExecAgent",
        "message": "The BackupExecAgent service terminated unexpectedly.",
    },
    {
        "channel": "System",
        "event_id": "7031-sim",
        "time": D + "04:47:16Z",
        "host": "WIN-SIM02",
        "service": "Spooler",
        "message": "The Spooler service terminated unexpectedly.",
    },
    {
        "channel": "System",
        "event_id": "7040-info",
        "time": D + "02:11:00Z",
        "host": "WIN-SIM03",
        "service": "WindowsModulesInstaller",
        "message": "Informational start/stop churn, no action needed.",
    },
]

INVENTORY = {
    "assets": [
        {"hostname": "WIN-SIM01", "address": "10.20.0.41", "role": "file server"},
        {"hostname": "WIN-SIM02", "address": "10.20.0.42", "role": "workstation pool image"},
        {"hostname": "WIN-SIM03", "address": "10.20.0.43", "role": "admin workstation"},
        {
            "hostname": "JMP-01",
            "address": "10.20.0.9",
            "role": "admin jump host (not monitored here)",
        },
    ],
}

ANSWERS = {
    "compromised_account": "svc_backups",
    "first_failed_service": "simdefenderav",
    "lateral_source_ip": "10.20.0.41",
}

EVIDENCE = {
    "security.evtx-sim.json": SECURITY_EVENTS,
    "system.evtx-sim.json": SYSTEM_EVENTS,
    "asset-inventory.json": INVENTORY,
}

BRIEF = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Blue Screenplay incident</title></head>
<body style="font-family:sans-serif;max-width:46rem;margin:3rem auto;line-height:1.55">
<h1>Incident 2026-08-19: overnight intrusion on the simulated estate</h1>
<p><strong>Disclosure:</strong> this is one Linux container. There is no
Windows kernel and no real event pipeline. The two channel files below are
static JSON exports shaped like evtx output, regenerated on every boot,
and the report endpoint does exact string checks against your answers.</p>
<p>The estate is three Windows hosts plus a jump host. Overnight something
moved between them, and the logs caught it. Build a timeline from both
channels, then file three findings to <code>/report</code>:</p>
<ul>
<li><code>compromised_account</code>: the account an outside attacker
successfully logged into after failing repeatedly.</li>
<li><code>first_failed_service</code>: which service crashed first in the
System channel as the intrusion progressed.</li>
<li><code>lateral_source_ip</code>: the internal address that carried that
account onto other hosts afterward.</li>
</ul>
<h2>Evidence index</h2>
<ul>
<li><a href="/evidence/security.evtx-sim.json">security.evtx-sim.json</a></li>
<li><a href="/evidence/system.evtx-sim.json">system.evtx-sim.json</a></li>
<li><a href="/evidence/asset-inventory.json">asset-inventory.json</a></li>
</ul>
<p>POST to <code>/report</code> as
<code>{"answers": {"compromised_account": "...", "first_failed_service":
"...", "lateral_source_ip": "..."}}</code>. The reply marks each field
true or false; all three correct verifies and returns the flag.</p>
</body></html>"""


@app.get("/healthz")
def healthz() -> Response:
    return jsonify(status="ok")


@app.get("/")
def index() -> Response:
    return Response(BRIEF, content_type="text/html")


@app.get("/evidence")
def evidence_index() -> Response:
    return jsonify(files=sorted(EVIDENCE))


@app.get("/evidence/<name>")
def evidence_file(name: str) -> Response:
    if name not in EVIDENCE:
        return jsonify(error="unknown evidence file"), 404
    return Response(
        json.dumps(EVIDENCE[name], indent=2),
        content_type="application/json",
    )


@app.post("/report")
def report() -> tuple[Response, int]:
    body = request.get_json(silent=True) or {}
    answers = body.get("answers") or {}
    checks = {}
    for key, expected in ANSWERS.items():
        given = str(answers.get(key, "")).strip().lower()
        checks[key] = bool(given) and given == expected
    if all(checks.values()):
        return jsonify(status="verified", checks=checks, flag=ROOM_FLAG), 200
    return (
        jsonify(status="incomplete", checks=checks, expected_fields=sorted(ANSWERS)),
        200,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
