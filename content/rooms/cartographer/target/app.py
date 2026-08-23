"""Waypoint Maps: the internal admin plane answers from outside. Room target only."""

import json
import os

from flask import Flask, Response

app = Flask(__name__)
FLAG = os.environ["ROOM_FLAG"]

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Waypoint Maps</title>
<style>
body { background:#F7F6F3; font-family:Helvetica,Arial,sans-serif; display:flex; justify-content:center; padding-top:10vh; }
.box { background:#fff; border:1px solid #EAEAEA; border-radius:8px; padding:2.5rem; width:30rem; }
h1 { letter-spacing:-0.02em; font-size:1.4rem; margin-bottom:1rem; }
p, li { color:#787774; font-size:.9rem; }
code, pre { background:#F7F6F3; border:1px solid #EAEAEA; border-radius:6px; padding:.15rem .4rem; font-size:.82rem; }
pre { padding:1rem; overflow:auto; }
.flag { background:#EDF3EC; color:#346538; border-radius:9999px; padding:.35rem 1rem; display:inline-block; }
</style></head><body>%s</body></html>"""


@app.get("/healthz")
def healthz():
    return "ok"


@app.get("/")
def home():
    return (
        PAGE
        % """
<div class="box">
<h1>Waypoint Maps</h1>
<p>Route planning for freight teams across Europe. Public map tiles and
delivery zones live under <code>/maps</code>.</p>
<p>Our operations tooling is not part of the public product. If you found
this page through a search engine, you already know more than most.</p>
<p><a href="/maps">Browse public maps</a></p>
</div>"""
    )


@app.get("/maps")
def maps():
    return (
        PAGE
        % """
<div class="box">
<h1>Public maps</h1>
<ul>
<li>EU trunk corridors, spring release</li>
<li>Benelux last-mile grid</li>
<li>Alpine winter pass status</li>
</ul>
<p>Tiles are served read-only. Route editing happens in the ops console,
which is not linked from here.</p>
</div>"""
    )


@app.get("/robots.txt")
def robots_txt():
    # The crawler rules were written by the same intern who indexed the
    # internal API docs.
    return Response(
        "User-agent: *\nDisallow: /api/openapi.json\nDisallow: /admin/\n",
        mimetype="text/plain",
    )


@app.get("/api/openapi.json")
def openapi_doc():
    spec = {
        "openapi": "3.1.0",
        "info": {
            "title": "Waypoint Maps internal API",
            "version": "0.9.2",
            "description": (
                "Operations endpoints for the Waypoint deploy pipeline. "
                "The front door blocks /admin/ in production; this "
                "sandbox keeps it reachable for on-call debugging."
            ),
        },
        "servers": [{"url": "http://localhost:8000"}],
        "paths": {
            "/healthz": {
                "get": {"summary": "Liveness probe", "responses": {"200": {"description": "ok"}}}
            },
            "/maps": {
                "get": {
                    "summary": "List public maps",
                    "responses": {"200": {"description": "HTML page"}},
                }
            },
            "/admin/backups/latest": {
                "get": {
                    "summary": "Download the latest nightly backup manifest",
                    "description": (
                        "Returns the manifest for the eu-central nightly "
                        "backup. The provisioning_token field is injected "
                        "by deploy agents and matches the cluster secret. "
                        "Internal use only."
                    ),
                    "responses": {"200": {"description": "Backup manifest as JSON"}},
                }
            },
        },
    }
    return Response(json.dumps(spec, indent=2), mimetype="application/json")


@app.get("/admin/backups/latest")
def backups_latest():
    manifest = {
        "artifact": "waypoint-nightly.tar.zst",
        "generated_utc": "2026-08-22T02:12:44Z",
        "region": "eu-central",
        "retention_days": 14,
        "provisioning_token": FLAG,
    }
    return Response(json.dumps(manifest, indent=2), mimetype="application/json")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
