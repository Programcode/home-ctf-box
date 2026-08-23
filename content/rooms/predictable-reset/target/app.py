"""ResetFlow: reset tokens derived from username and wall clock only. Room target only."""

import hashlib
import os
import time

from flask import Flask, Response, request
from markupsafe import escape

app = Flask(__name__)
FLAG = os.environ["ROOM_FLAG"]
TOKENS: dict[str, str] = {}

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>ResetFlow</title>
<style>
body { background:#F7F6F3; font-family:'Helvetica Neue',Helvetica,Arial,sans-serif; display:flex; justify-content:center; padding-top:12vh; }
.box { background:#fff; border:1px solid #EAEAEA; border-radius:8px; padding:2.5rem; width:26rem; }
h1 { font-family:Georgia,serif; letter-spacing:-0.02em; font-size:1.4rem; margin-bottom:1rem; }
p { color:#787774; font-size:.88rem; }
code { font-family:ui-monospace,Menlo,monospace; font-size:.85rem; background:#F7F6F3; border:1px solid #EAEAEA; border-radius:4px; padding:.1rem .4rem; }
strong { color:#111; }
</style></head><body>{BODY}</body></html>"""


def page(body):
    return PAGE.replace("{BODY}", body)


# The token is only the username glued to a 10-minute wall-clock window.
def current_token(username: str) -> str:
    return hashlib.md5(f"{username}:{int(time.time()) // 600}".encode()).hexdigest()


@app.get("/healthz")
def healthz():
    return "ok"


@app.get("/")
def index():
    return page(
        '<div class="box"><h1>ResetFlow</h1>'
        "<p>Forgot your password? We mint a fresh reset link every 10 minutes.</p>"
        "<p>Flow: <code>POST /forgot</code> then "
        "<code>GET /reset?username=&lt;user&gt;&amp;token=&lt;tok&gt;</code></p>"
        "<p>Links expire when the 10-minute window rolls over.</p></div>"
    )


@app.post("/forgot")
def forgot():
    username = request.form.get("username", "")
    if not username:
        return Response("missing user\n", status=400)
    TOKENS[username] = current_token(username)
    return Response(f"reset link generated for {escape(username)}\n", mimetype="text/plain")


@app.get("/reset")
def reset():
    username = request.args.get("username", "")
    token = request.args.get("token", "")
    if token != current_token(username):
        return Response("invalid token\n", status=403)
    return page(
        '<div class="box"><h1>Password reset</h1>'
        f"<p>A temporary password was issued for <strong>{escape(username)}</strong>.</p>"
        f"<p>New credentials: <code>{FLAG}</code></p></div>"
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
