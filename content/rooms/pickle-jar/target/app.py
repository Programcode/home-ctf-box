"""PickleJar: deliberately unsafe session restore. Room target only."""

import base64
import os
import pickle

from flask import Flask, Response, request
from markupsafe import escape

app = Flask(__name__)
FLAG = os.environ["ROOM_FLAG"]
FLAG_PATH = "/flag.txt"

with open(FLAG_PATH, "w") as fh:
    fh.write(FLAG)

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>PickleJar</title>
<style>
body { background:#F7F6F3; font-family:Helvetica,Arial,sans-serif; display:flex; justify-content:center; padding-top:12vh; }
.box { background:#fff; border:1px solid #EAEAEA; border-radius:8px; padding:2.5rem; width:26rem; }
h1 { letter-spacing:-0.02em; font-size:1.4rem; margin-bottom:1rem; }
p { color:#787774; font-size:.88rem; }
code { font-family:ui-monospace,Menlo,monospace; font-size:.85rem; background:#F7F6F3; border:1px solid #EAEAEA; border-radius:4px; padding:.1rem .4rem; }
.flag { background:#EDF3EC; color:#346538; border-radius:9999px; padding:.35rem 1rem; display:inline-block; }
</style></head><body>{BODY}</body></html>"""


@app.get("/healthz")
def healthz():
    return "ok"


@app.get("/")
def index():
    body = (
        '<div class="box"><h1>PickleJar</h1>'
        "<p>This service keeps session state as pickles. Restore a previous "
        "session by posting the base64-encoded pickle to "
        "<code>POST /load</code>.</p>"
        "<p>Do not load untrusted pickles. We are quite sure nobody ever will.</p></div>"
    )
    return PAGE.replace("{BODY}", body)


@app.post("/load")
def load():
    try:
        data = pickle.loads(base64.b64decode(request.get_data()))
        body = (
            '<div class="box"><h1>PickleJar</h1>'
            '<p class="flag">restored state: ' + escape(str(data)) + "</p></div>"
        )
        return PAGE.replace("{BODY}", body)
    except Exception as exc:
        return Response(
            "could not restore state: " + str(exc) + "\n",
            status=400,
            mimetype="text/plain",
        )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
