"""Gatehouse front desk: client identity taken from a spoofable header. Room target only."""

import os

from flask import Flask, Response, request

app = Flask(__name__)
FLAG = os.environ["ROOM_FLAG"]
OFFICE_ADDRESS = "127.0.0.1"

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Gatehouse</title>
<style>
body { background:#F7F6F3; font-family:Helvetica,Arial,sans-serif; display:flex; justify-content:center; padding-top:12vh; }
.box { background:#fff; border:1px solid #EAEAEA; border-radius:8px; padding:2.5rem; width:26rem; }
h1 { letter-spacing:-0.02em; font-size:1.4rem; margin-bottom:1rem; }
p { color:#787774; font-size:.88rem; }
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
        '<div class="box"><h1>Gatehouse</h1>'
        "<p>An internal panel waits at <code>/internal</code>. "
        "It answers only to callers from the office network (127.0.0.1).</p></div>"
    )


@app.get("/internal")
def internal() -> Response | str:
    forwarded = request.headers.get("X-Forwarded-For")
    claimed = forwarded.split(",")[0].strip() if forwarded else (request.remote_addr or "")
    if claimed == OFFICE_ADDRESS:
        return page(
            '<div class="box"><h1>Internal Panel</h1>'
            "<p>Office network confirmed. Panel reward:</p>"
            f"<span class='flag'>{FLAG}</span></div>"
        )
    return Response(
        f"office network only (your address reads {claimed})\n",
        status=403,
        mimetype="text/plain",
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
