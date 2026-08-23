"""Portal: deliberately injectable greeting endpoint. Room target only."""

import os

from flask import Flask, request

app = Flask(__name__)
FLAG = os.environ["ROOM_FLAG"]
CTX = {"user": "guest", "plan": "free", "flag": FLAG}

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Portal</title>
<style>
body { background:#F7F6F3; font-family:Helvetica,Arial,sans-serif; display:flex; justify-content:center; padding-top:12vh; }
.box { background:#fff; border:1px solid #EAEAEA; border-radius:8px; padding:2.5rem; width:26rem; }
h1 { letter-spacing:-0.02em; font-size:1.4rem; margin-bottom:1rem; }
h2 { font-size:1.1rem; margin:.2rem 0 .6rem; }
p { color:#787774; font-size:.88rem; }
code { font-family:ui-monospace,Menlo,monospace; font-size:.85rem; background:#F7F6F3; border:1px solid #EAEAEA; border-radius:4px; padding:.1rem .4rem; }
.flag { background:#EDF3EC; color:#346538; border-radius:9999px; padding:.35rem 1rem; display:inline-block; }
</style></head><body>__BODY__</body></html>"""


def page(body):
    return PAGE.replace("__BODY__", body)


@app.get("/healthz")
def healthz():
    return "ok"


@app.get("/")
def index():
    return page(
        '<div class="box"><h1>Portal</h1>'
        "<p>Tell us your name and we will greet you personally.</p>"
        "<p><code>GET /welcome?name=Ada</code></p></div>"
    )


@app.get("/welcome")
def welcome():
    name = request.args.get("name", "")
    fmt = "<h2>Welcome " + name + "</h2><p>Your plan: {plan}</p>"
    try:
        # The flaw: user input becomes part of the template itself.
        out = fmt.format(**CTX)
    except (KeyError, IndexError):
        return page('<div class="box"><h1>Oops</h1><p>bad name</p></div>')
    return page(f'<div class="box">{out}</div>')


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
