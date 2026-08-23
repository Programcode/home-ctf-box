"""Crumb & Co. loyalty portal: unsigned cookie forgery. Room target only."""

import base64
import json
import os

from flask import Flask, Response, request
from markupsafe import escape

app = Flask(__name__)
FLAG = os.environ["ROOM_FLAG"]

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Crumb &amp; Co.</title>
<style>
body { background:#F7F6F3; font-family:Helvetica,Arial,sans-serif; display:flex; justify-content:center; padding-top:12vh; }
.box { background:#fff; border:1px solid #EAEAEA; border-radius:8px; padding:2.5rem; width:26rem; }
h1 { letter-spacing:-0.02em; font-size:1.4rem; margin-bottom:1rem; }
p { color:#787774; font-size:.9rem; }
code { font-family:ui-monospace,Menlo,monospace; background:#F7F6F3; border-radius:4px; padding:.1rem .4rem; }
.flag { background:#EDF3EC; color:#346538; border-radius:9999px; padding:.35rem 1rem; display:inline-block; }
</style></head><body>{BODY}</body></html>"""


def page(body: str) -> str:
    return PAGE.replace("{BODY}", body)


@app.get("/healthz")
def healthz() -> str:
    return "ok"


@app.get("/")
def index() -> str:
    return page(
        '<div class="box"><h1>Crumb &amp; Co.</h1>'
        "<p>Loyalty members are identified by a <code>profile</code> cookie holding "
        "base64-encoded JSON. The kitchen never compares the recipe against a signature.</p>"
        "<p>The staff counter lives at <code>/admin-panel</code>.</p></div>"
    )


@app.get("/admin-panel")
def admin_panel() -> Response | str:
    raw = request.cookies.get("profile", "")
    if not raw:
        return page(
            '<div class="box"><h1>Staff counter</h1><p>No profile cookie, no service.</p></div>'
        )
    try:
        claims = json.loads(base64.b64decode(raw))
    except ValueError:
        return Response("malformed profile cookie\n", status=400, mimetype="text/plain")
    if not isinstance(claims, dict):
        return Response("malformed profile cookie\n", status=400, mimetype="text/plain")
    who = escape(str(claims.get("username", "unknown")))
    if claims.get("role") == "admin":
        return page(
            f'<div class="box"><h1>Staff counter</h1><p>Welcome back, {who}. Shift bonus:</p>'
            f"<span class='flag'>{FLAG}</span></div>"
        )
    return page(
        f'<div class="box"><h1>Staff counter</h1><p>{who} is not on the roster. Shoo.</p></div>'
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
