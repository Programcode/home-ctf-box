"""DocVault document portal: deliberately vulnerable to path traversal. Room target only."""

import os

from flask import Flask, Response, request

app = Flask(__name__)
FLAG = os.environ["ROOM_FLAG"]
DOCS = "/app/docs"
PRIVATE = "/app/private"

FILES = {
    "notes.txt": (
        "Q3 notes\n--------\n"
        "- migrate the file share off the old NAS before it dies\n"
        "- printer on floor 2 is haunted again\n"
    ),
    "meeting.txt": (
        "Standup 09:30\n-------------\n"
        "- everyone claims the outage was DNS\n"
        "- action item: stop blaming DNS\n"
    ),
    "todo.txt": "[x] write document portal\n[ ] sanitize the download name parameter\n",
}


def init() -> None:
    os.makedirs(DOCS, exist_ok=True)
    for name, content in FILES.items():
        with open(os.path.join(DOCS, name), "w") as fh:
            fh.write(content)
    # Deployment leaves its release record outside the public tree.
    os.makedirs(PRIVATE, exist_ok=True)
    with open(os.path.join(PRIVATE, "release-token.txt"), "w") as fh:
        fh.write(f"DocVault release record\ninstance token: {FLAG}\n")


init()

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>DocVault</title>
<style>
body { background:#F7F6F3; font-family:Helvetica,Arial,sans-serif; display:flex; justify-content:center; padding-top:12vh; }
.box { background:#fff; border:1px solid #EAEAEA; border-radius:8px; padding:2.5rem; width:26rem; }
h1 { font-family:Georgia,serif; letter-spacing:-0.02em; font-size:1.4rem; margin-bottom:1rem; }
li { margin:.4rem 0; } a { color:#111; }
p { color:#787774; font-size:.88rem; }
code { background:#F7F6F3; border:1px solid #EAEAEA; border-radius:4px; padding:.1rem .4rem; }
</style></head><body>%s</body></html>"""


@app.get("/healthz")
def healthz():
    return "ok"


@app.get("/")
def home():
    items = "".join(f'<li><a href="/download?name={n}">{n}</a></li>' for n in FILES)
    return PAGE % (
        '<div class="box"><h1>DocVault</h1>'
        "<p>Internal documents. Fetch any file by name:</p>"
        f"<ul>{items}</ul>"
        "<p style='margin-top:1rem;'>API: <code>GET /download?name=&lt;file&gt;</code></p></div>"
    )


@app.get("/download")
def download():
    name = request.args.get("name", "")
    if name.startswith(("/", "\\")):
        return Response("absolute paths are not allowed\n", status=400)
    try:
        with open(os.path.join(DOCS, name), "rb") as fh:
            data = fh.read()
    except OSError:
        return Response("file not found\n", status=404)
    return Response(data, mimetype="text/plain")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
