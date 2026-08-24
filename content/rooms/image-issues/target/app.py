"""Image layer investigation: an env file baked into a build layer. Room target only."""

import json
import os

from flask import Flask, Response, request
from markupsafe import escape

app = Flask(__name__)
FLAG = os.environ["ROOM_FLAG"]
DB_USER = "billing_ro"
DB_PASSWORD = "harbor-lantern-91"

L1 = "1c4d8a52f0e3b6a79d85f2c0b4a19e7d3f6c8b5a2e9d1f47c0b3a685d29e14f7"
L2 = "8e2f61b09c45d3a7e81f4c2b95a06d73f18c92e4ab57d0316fc89b24e70a53cd"
L3 = "b7d309e54a12cf83e96b41d72c58af60913d7e25cb48f69102ae37d5b6c80f42"
L4 = "e59c27ad83f1046be97d2513ca08bf64d21e58390ac6742fb19de3057846bc10"

MANIFEST = {
    "schemaVersion": 2,
    "mediaType": "application/vnd.oci.image.manifest.v1+json",
    "config": {
        "mediaType": "application/vnd.oci.image.config.v1+json",
        "digest": "sha256:9a41cc72e0b8d35fa62c81de47b09f5ac3d861e2f4ba07c95d8e63b1af24dc05",
        "size": 1204,
        "history": [
            {"created_by": "FROM python:3.12-alpine"},
            {"created_by": "COPY requirements.txt .", "layer": L1},
            {
                "created_by": "RUN pip install --no-cache-dir -r requirements.txt",
                "layer": L2,
            },
            {"created_by": "COPY . .", "layer": L3},
            {"created_by": 'CMD ["python", "app.py"]'},
        ],
    },
    "layers": [
        {"digest": f"sha256:{L1}", "size": 118},
        {"digest": f"sha256:{L2}", "size": 48213376},
        {"digest": f"sha256:{L3}", "size": 15230},
        {"digest": f"sha256:{L4}", "size": 0, "note": "metadata only"},
    ],
}

LISTINGS = {
    L1: """drwxr-xr-x root/root         0 .
-rw-r--r-- root/root       118 requirements.txt""",
    L2: """drwxr-xr-x root/root         0 usr/lib/python3.12/site-packages
drwxr-xr-x root/root         0 usr/lib/python3.12/site-packages/flask
-rw-r--r-- root/root    102417 usr/lib/python3.12/site-packages/flask/__init__.py
-rw-r--r-- root/root     88210 usr/lib/python3.12/site-packages/werkzeug/__init__.py
-rw-r--r-- root/root     41192 usr/lib/python3.12/site-packages/markupsafe/__init__.py""",
    L3: """drwxr-xr-x root/root         0 app
-rw-r--r-- root/root        97 app/.dockerignore
-rw-r--r-- root/root       220 app/.env
-rw-r--r-- root/root       198 app/.env.example
-rw-r--r-- root/root      3411 app/app.py
-rw-r--r-- root/root       118 app/requirements.txt
-rw-r--r-- root/root       512 app/README.md""",
    L4: "<empty layer: metadata only, no filesystem diff>",
}

ENV_FILE = """# billing-api runtime environment
# hotfix build 2026-06-30 from ops laptop (uncommitted changes included)
DB_HOST=postgres.internal
DB_PORT=5432
DB_NAME=billing
DB_USER=billing_ro
DB_PASSWORD=harbor-lantern-91
FLASK_ENV=production
"""

ENV_EXAMPLE = """# copy to .env and fill in locally
DB_HOST=localhost
DB_PORT=5432
DB_NAME=billing_dev
DB_USER=dev
DB_PASSWORD=change-me
FLASK_ENV=development
"""

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Image Issues</title>
<style>
body { background:#F7F6F3; font-family:Helvetica,Arial,sans-serif; display:flex; justify-content:center; padding-top:10vh; }
.box { background:#fff; border:1px solid #EAEAEA; border-radius:8px; padding:2.5rem; width:31rem; }
h1 { letter-spacing:-0.02em; font-size:1.4rem; margin-bottom:1rem; }
p, li { color:#787774; font-size:.88rem; line-height:1.5; }
code { font-family:ui-monospace,Menlo,monospace; font-size:.85rem; background:#F7F6F3; border:1px solid #EAEAEA; border-radius:4px; padding:.1rem .4rem; }
pre { background:#F7F6F3; border:1px solid #EAEAEA; border-radius:6px; padding:1rem; overflow:auto; font-size:.78rem; }
.flag { background:#EDF3EC; color:#346538; border-radius:9999px; padding:.3rem 1rem; font-family:ui-monospace,Menlo,monospace; font-size:.85rem; display:inline-block; }
.denied { color:#A33B3B; }
</style></head><body>{BODY}</body></html>"""


def page(body: str) -> str:
    return PAGE.replace("{BODY}", body)


@app.get("/healthz")
def healthz() -> str:
    return "ok"


@app.get("/")
def index() -> str:
    return page(
        '<div class="box"><h1>Case: billing-api production image review</h1>'
        "<p>The registry mirror exported the production image for a routine "
        "supply-chain audit after a scanner flagged the repo it came from. "
        "You get the manifest plus per-layer artifacts.</p>"
        "<p>Evidence:</p>"
        "<ul>"
        "<li><a href='/evidence/app-image-manifest.json'>app-image-manifest.json</a> "
        "(ordered layers and config history)</li>"
        "<li>Per-layer tar listings at <code>/evidence/layers/&lt;digest&gt;/tar-listing.txt</code></li>"
        "<li>Extracted layer files at <code>/evidence/layers/&lt;digest&gt;/fs/&lt;path&gt;</code></li>"
        "</ul>"
        "<p>Digests in URLs drop the sha256: prefix. The audit closes only "
        "when exposure is proven end to end: find credentials inside the "
        "image and demonstrate they unlock the live admin db console at "
        "<code>/admin/db</code>.</p></div>"
    )


@app.get("/evidence/app-image-manifest.json")
def manifest() -> Response:
    return Response(json.dumps(MANIFEST, indent=2), mimetype="application/json")


@app.get("/evidence/layers/<digest>/tar-listing.txt")
def listing(digest: str) -> Response:
    if digest not in LISTINGS:
        return Response("no such layer artifact\n", status=404, mimetype="text/plain")
    return Response(LISTINGS[digest] + "\n", mimetype="text/plain")


@app.get("/evidence/layers/<digest>/fs/<path:fspath>")
def layer_file(digest: str, fspath: str) -> Response:
    if digest == L3 and fspath == "app/.env":
        return Response(ENV_FILE, mimetype="text/plain")
    if digest == L3 and fspath == "app/.env.example":
        return Response(ENV_EXAMPLE, mimetype="text/plain")
    if digest in LISTINGS and fspath.startswith("usr/lib/python3.12"):
        return Response(
            "ELF or python source content elided in evidence export\n", mimetype="text/plain"
        )
    return page(
        '<div class="box"><h1 class="denied">Not in evidence bundle</h1>'
        f"<p>No extracted file <code>{escape(fspath[:80])}</code> exists for "
        "this layer.</p></div>",
    )


@app.route("/admin/db", methods=["GET", "POST"])
def admin_db() -> str:
    user = request.form.get("user") or request.args.get("user", "")
    password = request.form.get("password") or request.args.get("password", "")
    if user == DB_USER and password == DB_PASSWORD:
        return page(
            '<div class="box"><h1>Db console unlocked</h1>'
            "<p>Credentials accepted for billing_ro on postgres.internal. "
            "The image leak is confirmed against a live service.</p>"
            f"<span class='flag'>{FLAG}</span>"
            "<p>Remediation note: rotate the credential, rebuild from a "
            "clean tree with secret mounts, and add a registry gate that "
            "rejects env-shaped files in any layer.</p></div>"
        )
    return page(
        '<div class="box"><h1 class="denied">Console locked</h1>'
        "<p>The admin db console rejects those credentials.</p></div>"
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
