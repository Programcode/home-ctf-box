"""Internal admin console: loopback-only by design. Room target only."""

import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

FLAG = os.environ["ROOM_FLAG"]

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>{title}</title>
<style>
body {{ background:#F7F6F3; font-family:Helvetica,Arial,sans-serif; display:flex; justify-content:center; padding-top:12vh; }}
.box {{ background:#fff; border:1px solid #EAEAEA; border-radius:8px; padding:2.5rem; width:28rem; }}
h1 {{ letter-spacing:-0.02em; font-size:1.4rem; margin-bottom:1rem; }}
p, li {{ color:#787774; font-size:.9rem; line-height:1.5; }}
code {{ background:#F7F6F3; padding:.1rem .35rem; border-radius:4px; font-size:.85rem; }}
.flag {{ background:#EDF3EC; color:#346538; border-radius:9999px; padding:.35rem 1rem; display:inline-block; }}
</style></head><body>{body}</body></html>"""


class AdminHandler(BaseHTTPRequestHandler):
    def _respond(self, status: int, title: str, body: str) -> None:
        payload = PAGE.format(title=title, body=body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:  # noqa: N802 - stdlib naming
        if self.path == "/admin":
            self._respond(
                200,
                "Archive admin console",
                f"""
<div class="box">
<h1>Archive admin console</h1>
<p>Bound to loopback on purpose: the console trusts only traffic that
never left this machine. Session secret for this instance:</p>
<span class="flag">{FLAG}</span>
<p>If you can read this from a workstation, you came through a
tunnel.</p>
</div>""",
            )
        elif self.path == "/":
            self._respond(
                200,
                "Archive admin console",
                """
<div class="box">
<h1>Archive admin console</h1>
<p>Administrative functions live under <code>/admin</code>.</p>
</div>""",
            )
        else:
            self._respond(
                404,
                "Not found",
                """
<div class="box">
<h1>Not found</h1>
<p>The console serves <code>/</code> and <code>/admin</code>.</p>
</div>""",
            )

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        print(f"[admin] {self.address_string()} {format % args}")


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", 9001), AdminHandler)
    print("[admin] listening on 127.0.0.1:9001 (loopback only)")
    server.serve_forever()
