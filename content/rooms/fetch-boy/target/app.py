"""Peeker: URL preview proxy with an internal-only admin service. Room target only."""

import os
import threading
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

from flask import Flask, Response, request
from markupsafe import escape

app = Flask(__name__)
FLAG = os.environ["ROOM_FLAG"]
INTERNAL_PORT = 9001

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Peeker</title>
<style>
body { background:#F7F6F3; font-family:'Helvetica Neue',Helvetica,Arial,sans-serif; display:flex; justify-content:center; padding-top:12vh; }
.box { background:#fff; border:1px solid #EAEAEA; border-radius:8px; padding:2.5rem; width:30rem; }
h1 { font-family:Georgia,serif; letter-spacing:-0.02em; font-size:1.4rem; margin-bottom:1rem; }
p { color:#787774; font-size:.88rem; }
pre { font-family:ui-monospace,Menlo,monospace; font-size:.82rem; background:#F7F6F3; border:1px solid #EAEAEA; border-radius:4px; padding:.8rem; overflow:auto; white-space:pre-wrap; word-break:break-all; }
input[type=text] { width:100%; padding:.5rem .6rem; border:1px solid #EAEAEA; border-radius:6px; font-size:.9rem; box-sizing:border-box; }
button { margin-top:.6rem; padding:.45rem 1rem; border:none; border-radius:6px; background:#111; color:#fff; font-size:.85rem; cursor:pointer; }
</style></head><body>{BODY}</body></html>"""


def page(body):
    return PAGE.replace("{BODY}", body)


class AdminHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/admin":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(FLAG.encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass


def start_internal():
    # Loopback only: the admin service has no address on the room network.
    server = HTTPServer(("127.0.0.1", INTERNAL_PORT), AdminHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()


@app.get("/healthz")
def healthz():
    return "ok"


@app.get("/")
def index():
    return page(
        '<div class="box"><h1>Peeker</h1>'
        "<p>Paste any URL and we render a plain-text preview.</p>"
        '<form action="/fetch" method="get">'
        '<input type="text" name="url" placeholder="https://example.com/page">'
        '<button type="submit">Preview</button>'
        "</form></div>"
    )


@app.get("/fetch")
def fetch():
    url = request.args.get("url", "")
    if not url:
        return Response("missing url\n", status=400)
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:  # noqa: S310
            data = resp.read(2000).decode(errors="replace")
    except Exception as exc:
        return page(f'<div class="box"><h1>Preview failed</h1><pre>{escape(str(exc))}</pre></div>')
    return page(
        f'<div class="box"><h1>Preview of <code>{escape(url)}</code></h1>'
        f"<pre>{escape(data)}</pre></div>"
    )


start_internal()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
