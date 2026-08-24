#!/usr/bin/env python3
"""Knock daemon plus share server for the boot2root arc.

The daemon watches three TCP ports. A client that completes a
connect-and-close to 4010, 5011, 6012 in order within twelve seconds
unlocks the share server on 8080; until then nothing listens there.
Both services run unprivileged in one container.
"""

import os
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

KNOCK_SEQUENCE = [4010, 5011, 6012]
WINDOW_SECONDS = 12
SHARE_PORT = 8080

README = """SharePoint-ish appliance, incoming share (anonymous)

This server only exists after the gatekeeper accepts a knock, so if
you are reading this, you already know the ritual.

House rules:
- incoming is anonymous and world readable; treat it as public
- sysop-internal is for the sysop account only
- do NOT publish credential material into incoming again; last time
  the staff sync note ended up here for two weeks before anyone read
  the ticket
"""

CLEANUP = """cleanup queue:
- purge old sync notes from incoming (ticket OPS-77)
- remind staff that incoming is anonymous
- stop using the same password for ssh and shares (OPS-77 again)
"""

STAFF_SYNC = """staff device sync status, week 33

alice   laptop   ok
bob     phone    ok
carol   laptop   pending re-enroll
dave    tablet   ok
sysop   admin    ok   (console creds on file: sysop KnockFirstSync88)

reminder: rotate anything written into this file; see cleanup queue.
"""

FILES = {
    "readme.txt": README,
    "cleanup.txt": CLEANUP,
    "staff_sync.txt": STAFF_SYNC,
}

LISTING_PAGE = """<html><head><title>share browser</title></head><body>
<h1>share browser</h1>
<h2><a href="/share/incoming/">incoming</a> (anonymous)</h2>
<ul>{incoming_links}</ul>
<p>Also hosted: <a href="/share/sysop-internal/">sysop-internal</a>
(authenticated).</p>
</body></html>"""


class ShareHandler(BaseHTTPRequestHandler):
    server_version = "sharesim/1.0"

    def log_message(self, fmt: str, *args: object) -> None:  # noqa: A003
        pass

    def _send(self, code: int, body: str) -> None:
        payload = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:  # noqa: N802
        raw = self.path.split("?", 1)[0]
        path = raw.rstrip("/") or "/"
        if path == "/healthz":
            self._send(200, "ok")
        elif path == "/":
            links = "".join(
                f'<li><a href="/share/incoming/{name}">{name}</a></li>' for name in sorted(FILES)
            )
            self._send(200, LISTING_PAGE.format(incoming_links=links))
        elif path == "/share/incoming":
            links = "".join(
                f'<li><a href="/share/incoming/{name}">{name}</a></li>' for name in sorted(FILES)
            )
            body = f"<html><body><h2>incoming share (anonymous)</h2><ul>{links}</ul></body></html>"
            self._send(200, body)
        elif path.startswith("/share/incoming/"):
            name = raw.rstrip("/").rsplit("/", 1)[-1]
            if name in FILES:
                body = f"<html><body><pre>{FILES[name]}</pre></body></html>"
                self._send(200, body)
            else:
                self._send(404, "<html><body><p>no such file</p></body></html>")
        elif path == "/share/sysop-internal":
            self._send(
                401,
                "<html><body><p>sysop credentials required</p></body></html>",
            )
        else:
            self._send(404, "<html><body><p>not found</p></body></html>")


def start_share_server() -> None:
    server = ThreadingHTTPServer(("0.0.0.0", SHARE_PORT), ShareHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()


class KnockState:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.index = 0
        self.last = 0.0

    def register(self, port: int) -> None:
        with self.lock:
            if self.index < 0:
                return  # latched open
            now = time.monotonic()
            stale = self.index != 0 and (now - self.last) > WINDOW_SECONDS
            if port != KNOCK_SEQUENCE[self.index] or stale:
                self.index = 0
                self.last = 0.0
                return
            self.index += 1
            self.last = now
            if self.index == len(KNOCK_SEQUENCE):
                start_share_server()
                self.index = -1000


def watch_port(port: int, state: KnockState) -> None:
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("0.0.0.0", port))
    srv.listen(8)
    while True:
        conn, _addr = srv.accept()
        conn.close()
        state.register(port)


def main() -> None:
    os.umask(0o022)
    state = KnockState()
    for port in KNOCK_SEQUENCE:
        threading.Thread(target=watch_port, args=(port, state), daemon=True).start()
    threading.Event().wait()


if __name__ == "__main__":
    main()
