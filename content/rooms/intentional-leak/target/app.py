"""Pantryview intent router: exported-component and WebView-bridge sim. Room target only.

No Android runtime exists here. Activities, intents, the renderer, and
the settings store are Python data structures in one container, and
every mechanic mirrors a documented Android behavior the lesson maps.
"""

import hashlib
import hmac
import os
import re

from flask import Flask, jsonify, request

app = Flask(__name__)
FLAG = os.environ["ROOM_FLAG"]

DEBUG_TOKEN = hmac.new(FLAG.encode(), b"pantryview-debug-token", hashlib.sha256).hexdigest()[:24]

SETTINGS = {
    "debug_token": DEBUG_TOKEN,
    "sync_interval_seconds": "900",
    "last_pantry_scan": "2026-08-21T09:14:00Z",
}

ACTIVITIES = [
    {
        "name": ".MainActivity",
        "exported": True,
        "actions": ["android.intent.action.MAIN"],
        "extras": [],
        "notes": "launcher entry point, nothing sensitive",
    },
    {
        "name": ".NotesRenderActivity",
        "exported": True,
        "actions": ["com.pantryview.action.RENDER_NOTE"],
        "extras": ["note", "render_mode"],
        "notes": "debug build only: renders note extras through the webview template",
    },
    {
        "name": ".InternalDebugActivity",
        "exported": False,
        "actions": [],
        "extras": [],
        "notes": "internal diagnostics, guarded by token at /internal/debug",
    },
]

RENDER_ACTION = "com.pantryview.action.RENDER_NOTE"
BRIDGE_RE = re.compile(r"\{\{settings\.([a-z_]+)\}\}")

RENDER_LOG: list[str] = []

PAGE_TMPL = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Pantryview debug stack</title><style>
body {{ background:#F7F6F3; font-family:Helvetica,Arial,sans-serif; display:flex; justify-content:center; padding-top:8vh; }}
.wrap {{ width:44rem; padding-bottom:4rem; }}
.box {{ background:#fff; border:1px solid #EAEAEA; border-radius:8px; padding:1.5rem 2rem; margin-bottom:.8rem; }}
code, pre {{ background:#F7F6F3; border-radius:6px; padding:.15rem .4rem; font-size:.82rem; overflow-wrap:anywhere; }}
h1 {{ letter-spacing:-0.02em; font-size:1.35rem; }} h2 {{ font-size:1rem; }}
p, li {{ color:#787774; font-size:.9rem; line-height:1.55; }}
.disclosure {{ background:#FDF3E7; border:1px solid #EAD3AE; }}
</style></head><body><div class="wrap">{}</div></body></html>"""

HOME = """
<div class="box disclosure">
<h2>This is a simulation</h2>
<p>No device, emulator, or real application is involved. The activity
stack, intent router, webview-style renderer, and settings store are
data structures inside one disposable container built for teaching.
The debug token exists only inside this simulation.</p>
</div>
<div class="box">
<h1>Pantryview developer build</h1>
<p>The build exposes its component model over HTTP so you can rehearse
intent-based attacks without hardware:</p>
<pre>
GET  /api/activities            -&gt; component table (exported flags, filters)
POST /api/intent                -&gt; start an activity from JSON
GET  /api/render-log            -&gt; output of the notes renderer
GET  /internal/debug?token=...  -&gt; internal diagnostics desk
</pre>
<p>The router enforces exported flags like Android's activity manager,
and the renderer interpolates <code>{{settings.KEY}}</code>
expressions only while running its webview mode, which behaves like a
JavaScript bridge over app settings. The internal desk wants the debug
token the build keeps in its settings store.</p>
</div>
"""


@app.get("/healthz")
def healthz():
    return "ok"


@app.get("/")
def home():
    return PAGE_TMPL.format(HOME)


@app.get("/api/activities")
def activities():
    return jsonify({"package": "com.pantryview.app", "activities": ACTIVITIES})


@app.post("/api/intent")
def start_intent():
    body = request.get_json(silent=True) or {}
    component = str(body.get("component", "")).strip()
    action = str(body.get("action", ""))
    extras = body.get("extras") or {}
    if not isinstance(extras, dict):
        return jsonify({"error": "extras must be an object"}), 400

    record = next((a for a in ACTIVITIES if a["name"] == component), None)
    if record is None:
        return jsonify(
            {"error": f"ActivityNotFoundException: no component {component}", "type": "error"}
        ), 404
    if not record["exported"]:
        return jsonify(
            {
                "error": (
                    f"SecurityException: Permission Denial: starting Intent {{act={action!r}}} "
                    f"to {component} is not exported from com.pantryview.app"
                ),
                "type": "SecurityException",
            }
        ), 403
    if record["actions"] and action not in record["actions"]:
        return jsonify(
            {
                "error": (
                    f"ActivityNotFoundException: no activity found handling action "
                    f"{action!r} for {component}"
                ),
                "type": "ActivityNotFoundException",
            }
        ), 404

    if component == ".NotesRenderActivity":
        note = str(extras.get("note", ""))
        render_mode = str(extras.get("render_mode", "plain"))
        if render_mode == "webview":
            rendered = BRIDGE_RE.sub(_bridge_lookup, note)
        else:
            rendered = note
        line = f"[NotesRender/{render_mode}] {rendered}"
        RENDER_LOG.append(line)
        del RENDER_LOG[:-20]
        return jsonify({"started": component, "queued_render": True})
    return jsonify({"started": component, "queued_render": False})


def _bridge_lookup(match: re.Match) -> str:
    key = match.group(1)
    value = SETTINGS.get(key)
    if value is None:
        return "#bridge-miss#"
    return str(value)


@app.get("/api/render-log")
def render_log():
    return jsonify({"lines": list(RENDER_LOG)})


@app.get("/internal/debug")
def internal_debug():
    token = request.args.get("token", "")
    if hmac.compare_digest(token, DEBUG_TOKEN):
        return PAGE_TMPL.format(f"""
<div class="box">
<h1>Internal diagnostics</h1>
<p>Token accepted. Pantryview build 3.4.0-debug diagnostics unlocked:
renderer bridge reads settings keys without allowlisting, and secrets
land in renderer output. Filed as an exposure finding.</p>
<p><code>{FLAG}</code></p>
</div>""")
    return PAGE_TMPL.format("""
<div class="box">
<h1>Internal diagnostics</h1>
<p>Token rejected. The desk compares against the settings store's
debug_token. Find where the renderer can print it.</p>
</div>"""), 403


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, threaded=True)
