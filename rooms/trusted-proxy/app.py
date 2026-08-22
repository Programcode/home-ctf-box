from flask import Flask, Response, request
import os

app = Flask(__name__)
FLAG = os.environ["FLAG_13"]

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Gatehouse</title>
<style>
body { background:#F7F6F3; font-family:'Helvetica Neue',Helvetica,Arial,sans-serif; display:flex; justify-content:center; padding-top:12vh; }
.box { background:#fff; border:1px solid #EAEAEA; border-radius:8px; padding:2.5rem; width:26rem; }
h1 { font-family:Georgia,serif; letter-spacing:-0.02em; font-size:1.4rem; margin-bottom:1rem; }
p { color:#787774; font-size:.88rem; }
code { font-family:ui-monospace,Menlo,monospace; font-size:.85rem; background:#F7F6F3; border:1px solid #EAEAEA; border-radius:4px; padding:.1rem .4rem; }
.flag { background:#EDF3EC; color:#346538; border-radius:9999px; padding:.3rem 1rem; font-family:ui-monospace,Menlo,monospace; font-size:.85rem; display:inline-block; }
</style></head><body>{BODY}</body></html>"""


@app.route("/")
def index():
    return PAGE.replace(
        "{BODY}",
        '<div class="box"><h1>Gatehouse</h1>'
        "<p>An internal panel lives at <code>/internal</code>. "
        "It is only reachable from the office network (127.0.0.1).</p></div>",
    )


@app.route("/internal")
def internal():
    xff = request.headers.get("X-Forwarded-For")
    ip = xff.split(",")[0].strip() if xff else request.remote_addr
    if ip == "127.0.0.1":
        return PAGE.replace(
            "{BODY}",
            '<div class="box"><h1>Internal Panel</h1>'
            "<p>Office network confirmed. Panel reward:</p>"
            f"<span class='flag'>{FLAG}</span></div>",
        )
    return Response(
        f"internal network only (you are {ip})\n", status=403, mimetype="text/plain"
    )


app.run(host="0.0.0.0", port=5000)
