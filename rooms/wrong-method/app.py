from flask import Flask, Response, request
import os

app = Flask(__name__)
FLAG = os.environ["FLAG_14"]

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Nimbus Admin</title>
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
        '<div class="box"><h1>Nimbus Admin</h1>'
        "<p>The console at <code>/admin-console</code> blocks browser traffic. "
        "Only authorized tooling may pass.</p></div>",
    )


@app.route("/admin-console", methods=["GET", "PUT"])
def admin_console():
    if request.method == "GET":
        return Response(
            "browser requests are logged and blocked. authorized tooling may proceed.\n",
            status=403,
            mimetype="text/plain",
        )
    return PAGE.replace(
        "{BODY}",
        '<div class="box"><h1>Admin Console</h1>'
        "<p>Tooling session accepted. Console reward:</p>"
        f"<span class='flag'>{FLAG}</span></div>",
    )


app.run(host="0.0.0.0", port=5000)
