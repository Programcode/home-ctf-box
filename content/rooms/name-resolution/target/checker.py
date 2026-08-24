#!/usr/bin/env python3
"""Checker endpoint for the name-resolution room. Simulation only.

Accepts a captured SIM-HASH blob from the responder-sim exercise and
returns the room flag when the blob matches the deterministic value the
simulated responder produces for FILESRV01. No real hashing of real
credentials happens anywhere in this room.
"""

import hashlib
import hmac
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs

FLAG = os.environ.get("ROOM_FLAG", "FLAG{FLAGNOTSET0000000000000000}")
SEED = b"openrange-name-resolution-sim-v1"
EXPECTED = "SIM-HASH-" + hmac.new(SEED, b"FILESRV01", hashlib.sha256).hexdigest()[:32]

NOTICE = (
    "Simulation notice: every part of this exercise is a stand-in. The "
    "responder is a plain UDP logger, the captured blob is a labeled fake, "
    "and no real credentials exist on this box."
)

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Name Resolution Checker</title>
<style>
body { background:#F7F6F3; font-family:Helvetica,Arial,sans-serif; display:flex; justify-content:center; padding-top:10vh; }
.box { background:#fff; border:1px solid #EAEAEA; border-radius:8px; padding:2.5rem; width:34rem; }
h1 { letter-spacing:-0.02em; font-size:1.35rem; margin-bottom:.8rem; }
input { width:100%%; padding:.5rem .75rem; margin:.4rem 0; border:1px solid #EAEAEA; border-radius:6px; font-family:ui-monospace,Menlo,monospace; font-size:.85rem; }
button { background:#111; color:#fff; border:none; border-radius:6px; padding:.55rem 1rem; margin-top:.6rem; cursor:pointer; }
p, li { color:#787774; font-size:.9rem; }
.notice { border-left:3px solid #C9A227; padding-left:.8rem; }
.flag { background:#EDF3EC; color:#346538; border-radius:9999px; padding:.35rem 1rem; display:inline-block; }
</style></head><body>%s</body></html>"""


class Handler(BaseHTTPRequestHandler):
    def _page(self, body: str) -> None:
        data = (PAGE % body).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/healthz":
            self.send_response(200)
            self.send_header("Content-Length", "2")
            self.end_headers()
            self.wfile.write(b"ok")
            return
        if self.path == "/":
            self._page(
                "<div class='box'><h1>Capture Checker <small>(simulated)</small></h1>"
                f"<p class='notice'>{NOTICE}</p>"
                "<p>Paste the NTLMv2-SIM blob you captured from the responder "
                "log or reply packet.</p>"
                "<form method='post' action='/submit'>"
                "<input name='capture' placeholder='SIM-HASH-...' autocomplete='off'>"
                "<button type='submit'>Submit capture</button></form></div>"
            )
            return
        self._page("<div class='box'><h1>Not found</h1></div>")

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/submit":
            self._page("<div class='box'><h1>Not found</h1></div>")
            return
        length = int(self.headers.get("Content-Length") or 0)
        fields = parse_qs(self.rfile.read(length).decode(errors="replace"))
        submitted = (fields.get("capture") or [""])[0].strip().upper()
        if hmac.compare_digest(submitted, EXPECTED.upper()):
            self._page(
                "<div class='box'><h1>Capture verified</h1>"
                "<p>You reproduced the poisoning-to-capture flow end to end. "
                "Verification token for this session:</p>"
                f"<span class='flag'>{FLAG}</span></div>"
            )
            return
        self._page(
            "<div class='box'><h1>No match</h1>"
            "<p>That blob does not correspond to this session's simulated "
            "capture. Re-run the query client and copy the full value.</p>"
            "<p><a href='/'>Back to the checker</a></p></div>"
        )

    def log_message(self, fmt: str, *args) -> None:  # keep stdout tidy
        pass


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 8000), Handler).serve_forever()
