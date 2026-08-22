from flask import Flask, Response, request
from markupsafe import escape
import base64
import json
import os

app = Flask(__name__)
FLAG = os.environ["FLAG_8"]

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Cookie Shack</title>
<style>
body { background:#F7F6F3; font-family:'Helvetica Neue',Helvetica,Arial,sans-serif; display:flex; justify-content:center; padding-top:12vh; }
.box { background:#fff; border:1px solid #EAEAEA; border-radius:8px; padding:2.5rem; width:26rem; }
h1 { font-family:Georgia,serif; letter-spacing:-0.02em; font-size:1.4rem; margin-bottom:1rem; }
p { color:#787774; font-size:.88rem; }
code { font-family:ui-monospace,Menlo,monospace; font-size:.85rem; background:#F7F6F3; border:1px solid #EAEAEA; border-radius:4px; padding:.1rem .4rem; }
.flag { background:#EDF3EC; color:#346538; border-radius:9999px; padding:.3rem 1rem; font-family:ui-monospace,Menlo,monospace; font-size:.85rem; display:inline-block; }
</style></head><body>{BODY}</body></html>"""


def page(body):
    return PAGE.replace("{BODY}", body)


@app.route("/")
def index():
    return page(
        '<div class="box"><h1>Cookie Shack</h1>'
        "<p>Stateless auth! Your identity lives in a base64-encoded JSON cookie named <code>profile</code>.</p>"
        "<p>Staff hang out at <code>/admin-panel</code>.</p></div>"
    )


@app.route("/admin-panel")
def admin_panel():
    raw = request.cookies.get("profile", "")
    if not raw:
        return page(
            '<div class="box"><h1>Staff area</h1><p>No profile cookie presented.</p></div>'
        )
    try:
        obj = json.loads(base64.b64decode(raw))
    except Exception:
        return Response("malformed profile cookie\n", status=400, mimetype="text/plain")
    who = escape(str(obj.get("username", "unknown")))
    if obj.get("role") == "admin":
        return page(
            f'<div class="box"><h1>Staff area</h1><p>Welcome back, {who}. Session reward:</p>'
            f"<span class='flag'>{FLAG}</span></div>"
        )
    return page(
        f'<div class="box"><h1>Staff area</h1><p>{who} is not staff. Shoo.</p></div>'
    )


app.run(host="0.0.0.0", port=5000)
