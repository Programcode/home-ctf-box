"""Serverless abuse lab for the function-junction room.

A simulated function platform: one HTTP-triggered function has an
unauthenticated event source and a documented debug mode that attaches
process environment secrets to its webhook delivery. The learner's
collection endpoint is simulated at /sink because the lab network has
no internet. Deterministic, local, honest about its seams.
"""

import json
import os
import threading
import urllib.request

from flask import Flask, jsonify, request

app = Flask(__name__)
FLAG = os.environ["ROOM_FLAG"]

SECRETS_BLOB = (
    f"SMTP_PASSWORD=hunter2-sim;METRICS_TOKEN=rot-2026-09;"
    f"BACKUP_SIGNING_KEY={FLAG};SLACK_WEBHOOK=https://hooks.example.internal/none"
)

FUNCTIONS = {
    "thumbnailer": {
        "functionName": "thumbnailer",
        "runtime": "python3.12-sim",
        "triggers": [{"type": "storage-event", "auth": "signed"}],
        "description": "resizes uploads; invoke attempts require a signed trigger",
    },
    "webhook-relay": {
        "functionName": "webhook-relay",
        "runtime": "python3.12-sim",
        "triggers": [{"type": "http-event", "auth": "none"}],
        "description": (
            "relays JSON payloads to a caller-supplied destination_url; "
            "event source is unauthenticated (known misconfig)"
        ),
        "debug_mode": {
            "documented": True,
            "how": 'invoke with {"debug_hook": true}',
            "effect": ("diagnostics attach the process environment summary to the delivery body"),
        },
        "environment": ["SECRETS_BLOB"],
    },
}

SINK_LOCK = threading.Lock()
SINK_EVENTS: list[dict] = []


def _deliver(destination: str, body: dict) -> tuple[bool, str]:
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        destination,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return True, f"delivered, sink answered {resp.status}"
    except Exception as exc:  # noqa: BLE001 - delivery failures are data here
        return False, f"delivery failed: {exc.__class__.__name__}"


PAGE_HEAD = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>junction functions console</title>
<style>
body { background:#F7F6F3; font-family:Helvetica,Arial,sans-serif; display:flex; justify-content:center; padding-top:8vh; }
.box { background:#fff; border:1px solid #EAEAEA; border-radius:8px; padding:2.5rem; width:36rem; margin-bottom:1rem; }
h1 { letter-spacing:-0.02em; font-size:1.35rem; margin-bottom:1rem; }
p, li { color:#787774; font-size:.9rem; line-height:1.55; }
code { background:#F7F6F3; padding:.1rem .35rem; border-radius:4px; font-size:.85rem; }
.flag { background:#EDF3EC; color:#346538; border-radius:9999px; padding:.35rem 1rem; display:inline-block; }
a { color:#111; }
</style></head><body>"""


@app.get("/healthz")
def healthz():
    return "ok"


@app.get("/")
def home():
    return (
        PAGE_HEAD
        + """
<div class="box">
<h1>junction functions console</h1>
<p>A local simulation of a small serverless platform: two functions,
their trigger configurations, and an invoke endpoint per function.</p>
<p>Because your lab network cannot reach the internet, this appliance
also hosts a stand-in for your own webhook collector:</p>
<ul>
<li><code>POST /sink</code>: any JSON you point a delivery at lands here</li>
<li><code>GET /sink/events</code>: everything collected so far</li>
</ul>
<p>Endpoints: <code>GET /functions</code>,
<code>GET /functions/&lt;name&gt;</code>,
<code>POST /functions/&lt;name&gt;/invoke</code>.</p>
<p>This whole platform is one Flask process in your lab container.
No real serverless provider exists behind it.</p>
</div></body></html>"""
    )


@app.get("/functions")
def list_functions():
    return jsonify({"functions": list(FUNCTIONS.values())})


@app.get("/functions/<name>")
def function_detail(name: str):
    fn = FUNCTIONS.get(name)
    if not fn:
        return jsonify({"error": "NoSuchFunction"}), 404
    return jsonify(fn)


@app.post("/functions/<name>/invoke")
def invoke(name: str):
    fn = FUNCTIONS.get(name)
    if not fn:
        return jsonify({"error": "NoSuchFunction"}), 404

    if name == "thumbnailer":
        return (
            jsonify(
                {
                    "error": "SignedTriggerRequired",
                    "detail": "this function accepts storage events only",
                }
            ),
            403,
        )

    body = request.get_json(silent=True) or {}
    destination = str(body.get("destination_url", ""))
    if not destination.startswith(("http://", "https://")):
        return (
            jsonify(
                {
                    "error": "InvalidDestination",
                    "detail": "destination_url must be http(s); try your /sink collector",
                }
            ),
            400,
        )

    delivery = {
        "source": name,
        "payload": body.get("payload"),
        "debug_hook": bool(body.get("debug_hook")),
    }
    if delivery["debug_hook"]:
        delivery["diagnostics"] = {
            "note": (
                "debug mode attached the process environment; this is why "
                "debug flags never belong on production event handlers"
            ),
            "environment": {"SECRETS_BLOB": SECRETS_BLOB},
        }

    ok, note = _deliver(destination, delivery)
    return (
        jsonify(
            {
                "invocationId": f"fnv-{abs(hash(str(delivery))) % 1000000:06d}",
                "status": "delivered" if ok else "delivery-failed",
                "destination": destination,
                "note": note,
                "echo": {k: v for k, v in delivery.items() if k != "diagnostics"},
            }
        ),
        200 if ok else 502,
    )


@app.post("/sink")
def sink_post():
    data = request.get_json(silent=True) or {}
    with SINK_LOCK:
        SINK_EVENTS.append(data)
        index = len(SINK_EVENTS)
    return jsonify({"collected": index})


@app.get("/sink/events")
def sink_events():
    with SINK_LOCK:
        return jsonify({"count": len(SINK_EVENTS), "events": list(SINK_EVENTS)})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, threaded=True)
