from flask import Flask, Response, request
import hashlib
import os
import time
from markupsafe import escape

app = Flask(__name__)
FLAG = os.environ["FLAG_16"]
TOKENS = {}

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>ResetFlow</title>
<style>
body { background:#F7F6F3; font-family:'Helvetica Neue',Helvetica,Arial,sans-serif; display:flex; justify-content:center; padding-top:12vh; }
.box { background:#fff; border:1px solid #EAEAEA; border-radius:8px; padding:2.5rem; width:26rem; }
h1 { font-family:Georgia,serif; letter-spacing:-0.02em; font-size:1.4rem; margin-bottom:1rem; }
p { color:#787774; font-size:.88rem; }
code { font-family:ui-monospace,Menlo,monospace; font-size:.85rem; background:#F7F6F3; border:1px solid #EAEAEA; border-radius:4px; padding:.1rem .4rem; }
</style></head><body>__BODY__</body></html>"""


def page(body):
    return PAGE.replace("__BODY__", body)


def current_token(u):
    return hashlib.md5(f"{u}:{int(time.time()) // 600}".encode()).hexdigest()


@app.route("/")
def index():
    body = (
        '<div class="box"><h1>ResetFlow</h1>'
        "<p>Forgot your password? We mint a fresh reset link every 10 minutes.</p>"
        "<p>Flow: <code>POST /forgot</code> then <code>GET /reset?u=&lt;user&gt;&amp;token=&lt;tok&gt;</code></p>"
        "<p>Links expire when the 10-minute window rolls over.</p></div>"
    )
    return page(body)


@app.route("/forgot", methods=["POST"])
def forgot():
    u = request.values.get("u", "")
    if not u:
        return Response("missing user\n", status=400)
    tok = current_token(u)
    TOKENS[u] = tok
    return Response(f"reset link generated for {escape(u)}\n", mimetype="text/plain")


@app.route("/reset")
def reset():
    u = request.args.get("u", "")
    token = request.args.get("token", "")
    if token != current_token(u):
        return Response("invalid token\n", status=403)
    body = (
        f'<div class="box"><h1>Password reset</h1>'
        f"<p>A temporary password was issued for <strong>{escape(u)}</strong>.</p>"
        f"<p>New credentials: <code>{FLAG}</code></p></div>"
    )
    return page(body)


app.run(host="0.0.0.0", port=5000)
