from flask import Flask, Response, request
import os

app = Flask(__name__)
DOCS = "/app/docs"

FILES = {
    "notes.txt": (
        "Q3 notes\n--------\n"
        "- migrate the file share off the old NAS before it dies\n"
        "- printer on floor 2 is haunted again\n"
        "- remember to renew the TLS cert (it expired twice last year)\n"
    ),
    "meeting.txt": (
        "Standup 09:30\n-------------\n"
        "- everyone claims the outage was DNS\n"
        "- it was not DNS\n"
        "- action item: stop blaming DNS\n"
    ),
    "todo.txt": (
        "TODO\n----\n[x] write document portal\n[ ] sanitize the download path parameter\n[x] ship it anyway\n"
    ),
}


def init():
    os.makedirs(DOCS, exist_ok=True)
    for name, content in FILES.items():
        path = os.path.join(DOCS, name)
        if not os.path.exists(path):
            with open(path, "w") as fh:
                fh.write(content)


init()

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>DocVault</title>
<style>
body { background:#F7F6F3; font-family:'Helvetica Neue',Helvetica,Arial,sans-serif; display:flex; justify-content:center; padding-top:12vh; }
.box { background:#fff; border:1px solid #EAEAEA; border-radius:8px; padding:2.5rem; width:26rem; }
h1 { font-family:Georgia,serif; letter-spacing:-0.02em; font-size:1.4rem; margin-bottom:1rem; }
li { margin:.4rem 0; }
a { color:#111; }
p { color:#787774; font-size:.88rem; }
code { font-family:ui-monospace,Menlo,monospace; font-size:.85rem; background:#F7F6F3; border:1px solid #EAEAEA; border-radius:4px; padding:.1rem .4rem; }
</style></head><body>%s</body></html>"""


@app.route("/")
def index():
    items = "".join(f'<li><a href="/download?name={n}">{n}</a></li>' for n in FILES)
    return PAGE % (
        f'<div class="box"><h1>DocVault</h1>'
        f"<p>Internal documents. Fetch any file by name:</p>"
        f"<ul>{items}</ul>"
        f"<p style='margin-top:1rem;'>API: <code>GET /download?name=&lt;file&gt;</code></p></div>"
    )


@app.route("/download")
def download():
    name = request.args.get("name", "")
    if name.startswith(("/", "\\")):
        return Response("absolute paths are not allowed\n", status=400)
    path = os.path.join(DOCS, name)
    try:
        with open(path, "rb") as fh:
            data = fh.read()
    except OSError:
        return Response("file not found\n", status=404)
    return Response(data, mimetype="text/plain")


app.run(host="0.0.0.0", port=5000)
