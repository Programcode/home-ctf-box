#!/usr/bin/env python3
"""Manager console simulator on 8080.

A stand-in for a Java application manager: Basic auth, an HTML console
that documents exactly one action (deploying the flagcopy artifact),
and a small web tree. Deploying writes a copy of the application flag
into the published web path. No command execution exists here.
"""

import base64
import os
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs

PORT = 8080
MANAGER_USER = "manager"
MANAGER_PASS = "deploy1994"
FLAG_FILE = "/opt/services-everywhere/app.flag"
WEBAPPS = "/opt/tomcat-sim/webapps"

LANDING = """<html><head><title>Services Everywhere appliance</title></head>
<body>
<h1>Application host</h1>
<p>This appliance hosts the production webapp plus its management
console. The console lives under /manager/html.</p>
</body></html>"""

CONSOLE_PAGE = """<html><head><title>manager-sim console</title></head>
<body>
<h1>manager-sim</h1>
<p>Deployed artifacts:</p><ul><li>/webapp (running)</li></ul>
<h2>Deploy an artifact</h2>
<p>The console supports exactly one artifact. POST form field
<code>artifact=flagcopy</code> to <code>/manager/html/deploy</code>.
Deploying republishes a fresh copy of the application flag under
<code>/flagcopy/</code> for monitoring to verify.</p>
<form method="post" action="/manager/html/deploy">
<input name="artifact" value="flagcopy"><button type="submit">Deploy</button>
</form>
</body></html>"""


def read_flag() -> str:
    with open(FLAG_FILE, encoding="utf-8") as fh:
        return fh.read().strip()


def deploy_flagcopy() -> str:
    token = secrets.token_hex(4)
    out_dir = os.path.join(WEBAPPS, "flagcopy")
    os.makedirs(out_dir, exist_ok=True)
    page = (
        "<html><body><h1>flagcopy artifact</h1>"
        f"<p>FLAG={read_flag()}</p>"
        f"<p>deployment {token}</p></body></html>"
    )
    with open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(page)
    return token


class Handler(BaseHTTPRequestHandler):
    server_version = "manager-sim/1.0"

    def log_message(self, fmt: str, *args: object) -> None:  # noqa: A003
        pass

    def _authed(self) -> bool:
        header = self.headers.get("Authorization", "")
        if not header.startswith("Basic "):
            return False
        try:
            decoded = base64.b64decode(header[6:].strip()).decode("utf-8")
            user, _, password = decoded.partition(":")
        except Exception:
            return False
        return secrets.compare_digest(user, MANAGER_USER) and secrets.compare_digest(
            password, MANAGER_PASS
        )

    def _send(self, code: int, body: str, ctype: str = "text/html; charset=utf-8") -> None:
        payload = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0].rstrip("/") or "/"
        if path == "/healthz":
            self._send(200, "ok", "text/plain")
        elif path == "/":
            self._send(200, LANDING)
        elif path == "/flagcopy/" or path == "/flagcopy":
            index = os.path.join(WEBAPPS, "flagcopy", "index.html")
            if os.path.exists(index):
                with open(index, encoding="utf-8") as fh:
                    self._send(200, fh.read())
            else:
                self._send(404, "<html><body><p>artifact not deployed yet</p></body></html>")
        elif path == "/manager/html":
            if not self._authed():
                self.send_response(401)
                self.send_header("WWW-Authenticate", 'Basic realm="manager-sim"')
                self._send(401, "<html><body><p>authentication required</p></body></html>")
            else:
                self._send(200, CONSOLE_PAGE)
        else:
            self._send(404, "<html><body><p>not found</p></body></html>")

    def do_POST(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0]
        if path != "/manager/html/deploy":
            self._send(404, "<html><body><p>not found</p></body></html>")
            return
        if not self._authed():
            self.send_response(401)
            self.send_header("WWW-Authenticate", 'Basic realm="manager-sim"')
            self._send(401, "<html><body><p>authentication required</p></body></html>")
            return
        length = int(self.headers.get("Content-Length") or 0)
        form = parse_qs(self.rfile.read(length).decode("utf-8"))
        artifact = (form.get("artifact") or [""])[0]
        if artifact != "flagcopy":
            self._send(
                400,
                "<html><body><p>unknown artifact; the console deploys only "
                "the documented flagcopy artifact</p></body></html>",
            )
            return
        token = deploy_flagcopy()
        self._send(
            200,
            "<html><body><h1>deployment complete</h1>"
            f"<p>artifact flagcopy deployed as /flagcopy/ (id {token})</p>"
            "</body></html>",
        )


def main() -> None:
    os.makedirs(WEBAPPS, exist_ok=True)
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    t.join()


if __name__ == "__main__":
    main()
