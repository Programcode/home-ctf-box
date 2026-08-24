"""Audit-log analysis lab for the cloudtrail-of-crumbs room.

Serves a deterministic simulated cloud audit trail as evidence and a
report desk that checks three incident-analysis answers. Everything is
a local simulation: no real cloud account or network is involved.
"""

import os
from pathlib import Path

from flask import Flask, Response, request

app = Flask(__name__)
FLAG = os.environ["ROOM_FLAG"]

EVIDENCE_PATH = Path(__file__).parent / "evidence" / "cloudtrail-sim.json"

LEAKED_KEY_USER = "ci-deployer"
PERSISTED_KEY_USER = "backup-archiver"
EXPOSURE_ACTION = "put_bucket_policy"

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Case IR-2026-08-19-04: leaked key chain</title>
<style>
body { background:#F7F6F3; font-family:Helvetica,Arial,sans-serif; display:flex; justify-content:center; padding-top:10vh; }
.box { background:#fff; border:1px solid #EAEAEA; border-radius:8px; padding:2.5rem; width:34rem; }
h1 { letter-spacing:-0.02em; font-size:1.35rem; margin-bottom:1rem; }
p, li { color:#787774; font-size:.9rem; line-height:1.55; }
code { background:#F7F6F3; padding:.1rem .35rem; border-radius:4px; font-size:.85rem; }
.flag { background:#EDF3EC; color:#346538; border-radius:9999px; padding:.35rem 1rem; display:inline-block; }
a { color:#111; }
</style></head><body>%s</body></html>"""


@app.get("/healthz")
def healthz():
    return "ok"


@app.get("/")
def home():
    return (
        PAGE
        % """
<div class="box">
<h1>Case IR-2026-08-19-04: leaked key chain</h1>
<p>Overnight, the operations bucket <code>nimbus-prod-backups</code>
started serving its contents to strangers. The audit trail survived
and has been exported for review.</p>
<p>Evidence: <a href="/evidence/cloudtrail-sim.json">cloudtrail-sim.json</a>
(deterministic simulated event stream).</p>
<p>The report desk closes the case when you can answer all three
questions with exact values pulled from the log:</p>
<ul>
<li><code>q1</code>: which IAM user's long-lived access key did the
thief reuse?</li>
<li><code>q2</code>: which IAM user received the fresh access key the
thief minted for persistence?</li>
<li><code>q3</code>: which API action opened the bucket to anonymous
reads?</li>
</ul>
<p>Submit them together:
<code>GET /report?q1=...&amp;q2=...&amp;q3=...</code></p>
<p>This box is a local simulation. The log is static JSON, the report
desk is a Flask route, and nothing here touches a real cloud provider.</p>
</div>"""
    )


@app.get("/evidence/cloudtrail-sim.json")
def evidence():
    return Response(
        EVIDENCE_PATH.read_bytes(),
        mimetype="application/json",
        headers={"Content-Disposition": "attachment; filename=cloudtrail-sim.json"},
    )


def _clean(value: str) -> str:
    return value.strip().lower()


@app.get("/report")
def report():
    q1 = _clean(request.args.get("q1", ""))
    q2 = _clean(request.args.get("q2", ""))
    q3 = _clean(request.args.get("q3", ""))
    if q1 == LEAKED_KEY_USER and q2 == PERSISTED_KEY_USER and q3 == EXPOSURE_ACTION:
        return (
            PAGE
            % f"""
<div class="box">
<h1>Case closed</h1>
<p>Your reconstruction matches the trail: a long-lived key for
<code>{LEAKED_KEY_USER}</code> was reused from an outside address,
that session assumed a role, minted a new key for
<code>{PERSISTED_KEY_USER}</code>, and finally rewrote the bucket
policy so anonymous clients could list and fetch everything.</p>
<span class="flag">{FLAG}</span>
<p>Remediation note: rotate the exposed key, disable the minted one,
scope policies away from <code>Principal: *</code>, and alert on
<code>CreateAccessKey</code> issued by anyone other than the account
owner.</p>
</div>"""
        )
    wrong = []
    if q1 != LEAKED_KEY_USER:
        wrong.append("q1")
    if q2 != PERSISTED_KEY_USER:
        wrong.append("q2")
    if q3 != EXPOSURE_ACTION:
        wrong.append("q3")
    listed = ", ".join(wrong)
    return (
        PAGE
        % f"""
<div class="box">
<h1>Report rejected</h1>
<p>These answers do not match the evidence yet:
<code>{listed}</code>. Walk the events in time order and separate the
routine traffic from the night of the incident.</p>
</div>""",
        403,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, threaded=True)
