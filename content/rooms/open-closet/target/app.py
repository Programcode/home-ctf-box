"""Backup Closet: nightly database dumps behind an unauthenticated listing. Room target only."""

import os

from flask import Flask, Response
from markupsafe import escape

app = Flask(__name__)
FLAG = os.environ["ROOM_FLAG"]
BACKUPS = "/app/backups"

FILES = {
    "db_dump_2026.sql": (
        "-- nimbus crm dump 2026-08\n"
        "CREATE TABLE vault(secret TEXT);\n"
        f"INSERT INTO vault VALUES ('{FLAG}');\n"
    ),
    "db_dump_2025.sql": (
        "-- older dump, mostly coupons\nINSERT INTO coupons VALUES ('WELCOME10');\n"
    ),
    "notes.md": "# ops notes\nrotation overdue since Q1\n",
}

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Backup Closet</title>
<style>
body { background:#F7F6F3; font-family:'Helvetica Neue',Helvetica,Arial,sans-serif; display:flex; justify-content:center; padding-top:12vh; }
.box { background:#fff; border:1px solid #EAEAEA; border-radius:8px; padding:2.5rem; width:26rem; }
h1 { font-family:Georgia,serif; letter-spacing:-0.02em; font-size:1.4rem; margin-bottom:1rem; }
li { margin:.35rem 0; }
a { color:#111; }
p { color:#787774; font-size:.88rem; }
code { font-family:ui-monospace,Menlo,monospace; font-size:.85rem; background:#F7F6F3; border:1px solid #EAEAEA; border-radius:4px; padding:.1rem .4rem; }
</style></head><body>{BODY}</body></html>"""


def init():
    os.makedirs(BACKUPS, exist_ok=True)
    for name, content in FILES.items():
        with open(os.path.join(BACKUPS, name), "w") as fh:
            fh.write(content)


init()


def page(body):
    return PAGE.replace("{BODY}", body)


@app.get("/healthz")
def healthz():
    return "ok"


@app.get("/")
def home():
    return page(
        '<div class="box"><h1>Backup Closet</h1>'
        "<p>Ops area. Nightly dumps land under <code>/backups/</code>.</p></div>"
    )


@app.get("/backups/")
def listing():
    items = "".join(
        f'<li><a href="/backups/{escape(n)}">{escape(n)}</a></li>'
        for n in sorted(os.listdir(BACKUPS))
    )
    return page(
        '<div class="box"><h1>Backup Closet</h1>'
        "<p>Automated nightly dumps:</p>"
        f"<ul>{items}</ul></div>"
    )


@app.get("/backups/<name>")
def serve(name):
    if name.startswith(("/", "\\")) or ".." in name:
        return Response("invalid path\n", status=400, mimetype="text/plain")
    try:
        with open(os.path.join(BACKUPS, name), "rb") as fh:
            data = fh.read()
    except OSError:
        return Response("file not found\n", status=404, mimetype="text/plain")
    return Response(data, mimetype="text/plain")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
