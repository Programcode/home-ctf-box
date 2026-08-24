"""SOC training desk: fixed synthetic alert queue for triage practice.

All alerts are invented, classification state lives in this process
only, and nothing here contacts a real security product or feed.
"""

import os

from flask import Flask, Response, request

app = Flask(__name__)
FLAG = os.environ["ROOM_FLAG"]


def ground_truth(alert: dict) -> str:
    """Desk playbook rule: intel confirmation with no covering ticket."""
    if alert["intel_hit"] and alert["change_ticket"] is None:
        return "true_positive"
    return "false_positive"


# Ground truth per the same rule taught in the lesson and the playbook.
ALERTS = [
    {
        "id": "ALT-1001",
        "title": "Impossible travel sign-in for j.wu",
        "severity": "high",
        "detected_at": "2026-08-14T02:41:07Z",
        "src_ip": "45.61.186.9",
        "account": "j.wu",
        "intel_hit": True,
        "change_ticket": None,
        "summary": "Sign-in from Budapest followed 11 minutes later by a sign-in flagged to an ASN with no office presence; source IP is on two intel lists.",
    },
    {
        "id": "ALT-1002",
        "title": "Known loader hash blocked on workstation WS-2214",
        "severity": "critical",
        "detected_at": "2026-08-14T02:47:33Z",
        "src_ip": "10.40.18.77",
        "account": "m.reyes",
        "intel_hit": True,
        "change_ticket": None,
        "summary": "EDR quarantined a DLL whose SHA-256 matches a loader family tracked since June; hash is confirmed malicious by intel.",
    },
    {
        "id": "ALT-1003",
        "title": "Bulk file download by svc-backup",
        "severity": "medium",
        "detected_at": "2026-08-14T02:52:10Z",
        "src_ip": "10.20.5.31",
        "account": "svc-backup",
        "intel_hit": False,
        "change_ticket": "CHG-2291",
        "summary": "Service account read 4,120 objects in 12 minutes from the records share; volume matches the nightly sync window covered by approved change CHG-2291.",
    },
    {
        "id": "ALT-1004",
        "title": "Internal port scan detected",
        "severity": "low",
        "detected_at": "2026-08-14T03:01:44Z",
        "src_ip": "10.20.0.140",
        "account": "svc-vulnscan",
        "intel_hit": False,
        "change_ticket": "CHG-2305",
        "summary": "Sequential connect attempts against the finance segment originate from the vulnerability scanner appliance during its quarterly window under CHG-2305.",
    },
    {
        "id": "ALT-1005",
        "title": "Encoded PowerShell command on jump host",
        "severity": "high",
        "detected_at": "2026-08-14T03:09:26Z",
        "src_ip": "10.40.7.3",
        "account": "a.kovacs",
        "intel_hit": True,
        "change_ticket": None,
        "summary": "Base64-encoded PowerShell decoded to a DownloadString cradle pulling from a raw-IP URL; parent process is winword.exe and intel flags the destination as staging infrastructure.",
    },
    {
        "id": "ALT-1006",
        "title": "Brute force pattern from load balancer",
        "severity": "medium",
        "detected_at": "2026-08-14T03:14:58Z",
        "src_ip": "10.20.9.10",
        "account": "-",
        "intel_hit": False,
        "change_ticket": None,
        "summary": "Hundreds of failed authentications per minute share one fingerprint; they are health checks whose probe credentials expired after a config push. Intel has no record of the source.",
    },
    {
        "id": "ALT-1007",
        "title": "Data staging to external storage domain",
        "severity": "critical",
        "detected_at": "2026-08-14T03:22:41Z",
        "src_ip": "10.40.19.52",
        "account": "l.nagy",
        "intel_hit": True,
        "change_ticket": "CHG-2310",
        "summary": "DLP saw 2.1 GB written to a cloud drive domain that also appears in intel data. CHG-2310 approves l.nagy to migrate archive media to that exact tenant this week.",
    },
    {
        "id": "ALT-1008",
        "title": "Beaconing to uncategorized domain",
        "severity": "low",
        "detected_at": "2026-08-14T03:30:19Z",
        "src_ip": "10.40.22.61",
        "account": "s.farkas",
        "intel_hit": False,
        "change_ticket": None,
        "summary": "Regular HTTPS requests to a marketing analytics domain the proxy has not categorized yet; interval matches a vendor SDK documented in the asset register and intel lists the domain as benign.",
    },
]

_verdicts: dict[str, str] = {}

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>SOC desk: alert queue triage</title>
<style>
body { background:#F7F6F3; font-family:Helvetica,Arial,sans-serif; display:flex; justify-content:center; padding-top:12vh; }
.box { background:#fff; border:1px solid #EAEAEA; border-radius:8px; padding:2.5rem; width:34rem; }
h1 { letter-spacing:-0.02em; font-size:1.35rem; margin-bottom:1rem; }
p, li { color:#787774; font-size:.9rem; line-height:1.55; }
code { background:#F7F6F3; padding:.1rem .35rem; border-radius:4px; font-size:.85rem; }
.flag { background:#EDF3EC; color:#346538; border-radius:9999px; padding:.35rem 1rem; display:inline-block; }
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
<h1>SOC desk: alert queue triage</h1>
<p>Eight detections from last night are waiting for human review.
Fetch them from <code>GET /alerts</code>, decide each one using the
desk playbook, then submit verdicts one at a time:
<code>POST /classify</code> with JSON
<code>{"alert_id":"...","verdict":"true_positive"}</code> or
<code>false_positive</code>.</p>
<p>The playbook rule: true positive requires <code>intel_hit == true</code>
AND <code>change_ticket == null</code>. An intel hit with an approved
change ticket behind it is explained activity, and no intel hit means
the detector alone cannot confirm malice.</p>
<p>A correct full set returns the room flag.</p>
</div>"""
    )


@app.get("/alerts")
def list_alerts():
    return {
        "playbook": "true_positive iff intel_hit == true AND change_ticket is null",
        "count": len(ALERTS),
        "classified": sorted(_verdicts),
        "alerts": ALERTS,
    }


@app.post("/classify")
def classify():
    body = request.get_json(silent=True) or {}
    alert_id = str(body.get("alert_id", ""))
    verdict = str(body.get("verdict", ""))
    alert = next((a for a in ALERTS if a["id"] == alert_id), None)
    if alert is None:
        return Response('{"error": "unknown alert_id"}', mimetype="application/json"), 400
    if verdict not in {"true_positive", "false_positive"}:
        return (
            Response(
                '{"error": "verdict must be true_positive or false_positive"}',
                mimetype="application/json",
            ),
            400,
        )

    _verdicts[alert_id] = verdict
    payload = {
        "alert_id": alert_id,
        "recorded": verdict,
        "progress": f"{len(_verdicts)}/{len(ALERTS)} classified",
    }

    if len(_verdicts) < len(ALERTS):
        return payload

    wrong = sorted(a["id"] for a in ALERTS if _verdicts[a["id"]] != ground_truth(a))
    if wrong:
        payload.update({"queue_status": "rejected", "wrong_ids": wrong})
        return payload

    payload.update({"queue_status": "closed", "flag": FLAG})
    return payload


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, threaded=True)
