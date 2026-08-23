"""Nimbus admin console: access decided by the HTTP verb alone. Room target only."""

import os

from flask import Flask, Response, request

app = Flask(__name__)
FLAG = os.environ["ROOM_FLAG"]

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Nimbus Admin</title>
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
        '<div class="box"><h1>Nimbus Admin</h1>'
        "<p>The console at <code>/admin-console</code> blocks browser traffic. "
        "Only authorized tooling gets through.</p></div>"
    )


@app.route("/admin-console", methods=["GET", "PUT", "DELETE"])
def admin_console() -> Response | str:
    if request.method == "GET":
        return Response(
            "browser requests are logged and blocked. authorized tooling may proceed.\n",
            status=403,
            mimetype="text/plain",
        )
    return page(
        '<div class="box"><h1>Admin Console</h1>'
        "<p>Tooling session accepted. Console reward:</p>"
        f"<span class='flag'>{FLAG}</span></div>"
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
