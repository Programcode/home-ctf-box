"""Signal Harbor status board: an unkeyed host header poisons the page cache. Room target only."""

import os
import threading
import time

from flask import Flask, request

app = Flask(__name__)
FLAG = os.environ["ROOM_FLAG"]

CACHE_TTL_SECONDS = 300
_cache: dict[str, tuple[float, str]] = {}
_cache_lock = threading.Lock()

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Signal Harbor</title>
<style>
body { background:#F7F6F3; font-family:Helvetica,Arial,sans-serif; display:flex; justify-content:center; padding-top:10vh; }
.box { background:#fff; border:1px solid #EAEAEA; border-radius:8px; padding:2.5rem; width:32rem; }
h1 { letter-spacing:-0.02em; font-size:1.4rem; margin-bottom:1rem; }
p, li, td { color:#787774; font-size:.9rem; }
table { border-collapse:collapse; width:100%%; margin-top:.5rem; }
td, th { text-align:left; padding:.35rem .5rem; border-bottom:1px solid #EAEAEA; }
code { background:#F7F6F3; border:1px solid #EAEAEA; border-radius:6px; padding:.15rem .4rem; font-size:.82rem; }
.badge { background:#EDF3EC; color:#346538; border-radius:9999px; padding:.25rem .8rem; display:inline-block; font-size:.8rem; }
a { color:#346538; }
</style></head><body>%s</body></html>"""


def render_status(host: str) -> str:
    rows = "".join(
        f"<tr><td>{region}</td><td>{depth}</td></tr>"
        for region, depth in (("BUD-1", "0 queued"), ("FRA-2", "2 queued"), ("WAW-3", "0 queued"))
    )
    diagnostics = ""
    if host.endswith(".internal"):
        # Reverse-proxy routing trusts this header, and internal hosts get
        # verbose diagnostics, deploy banner included.
        diagnostics = (
            f"<p><span class='badge'>internal diagnostics enabled for {host}</span></p>"
            f"<!-- deploy-banner: {FLAG} -->"
        )
    return (
        '<div class="box"><h1>Signal Harbor fleet status</h1>'
        f"<table><tr><th>Region</th><th>Ingest queue</th></tr>{rows}</table>"
        f"<p>Rendered for host <code>{host}</code> at {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}.</p>"
        f"{diagnostics}</div>"
    )


@app.get("/healthz")
def healthz():
    return "ok"


@app.get("/")
def home():
    return (
        PAGE
        % """
<div class="box">
<h1>Signal Harbor</h1>
<p>Telemetry ingest for small satellite fleets. The public status board
at <code>/status</code> is served through our edge page cache.</p>
<p><a href="/status">Open the status board</a></p>
</div>"""
    )


@app.get("/status")
def status():
    now = time.monotonic()
    with _cache_lock:
        hit = _cache.get(request.path)
    forwarded_host = request.headers.get("X-Forwarded-Host")
    # Requests without the routing header are served from the store while
    # the entry lives. Anything carrying one goes to the origin like a
    # miss, and whatever comes back becomes the stored copy for the path.
    if forwarded_host is None and hit is not None and hit[0] > now:
        return hit[1] + "\n<!-- served-from-cache: true -->"
    host = forwarded_host or request.host
    body = render_status(host)
    with _cache_lock:
        _cache[request.path] = (now + CACHE_TTL_SECONDS, body)
    return body + "\n<!-- served-from-cache: false -->"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
