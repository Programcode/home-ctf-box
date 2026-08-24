"""Dependency confusion lab: simulated registry that records hostile publishes. Room target only."""

import json
import os
import re

from flask import Flask, Response, jsonify, request

app = Flask(__name__)
FLAG = os.environ["ROOM_FLAG"]
MAINTAINER_TOKEN = "npm_d2ef234f04b0272293cd64e033568dee"
CANARY_URL = "http://canary.company.internal/beacon?pkg=company-utils"

REGISTRY = {
    "name": "company-utils",
    "readme": "Internal helpers for billing and invoicing jobs.",
    "dist-tags": {"latest": "1.0.0"},
    "versions": {
        "1.0.0": {
            "scripts": {"postinstall": "node scripts/setup.js"},
            "dependencies": {"lodash": "^4.17.21"},
        }
    },
}

NPMRC_ARTIFACT = """# ci-artifacts/archive-2026-06-14/workspace/.npmrc
# snapshot of the runner workspace taken by the nightly artifact job
registry=http://registry.company.internal/
//registry.company.internal/:_authToken=npm_d2ef234f04b0272293cd64e033568dee
//registry.company.internal/:always-auth=true
scope=@company
company:registry=http://registry.company.internal/
"""

state = {"takeover": None}


def _page(body: str, status: int = 200) -> Response:
    html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Dependency Confusion Lab</title>
<style>
body {{ background:#F7F6F3; font-family:Helvetica,Arial,sans-serif; display:flex; justify-content:center; padding-top:8vh; }}
.box {{ background:#fff; border:1px solid #EAEAEA; border-radius:8px; padding:2.5rem; width:32rem; }}
h1 {{ letter-spacing:-0.02em; font-size:1.35rem; margin-bottom:1rem; }}
h2 {{ font-size:1rem; margin-top:1.4rem; }}
p, li {{ color:#787774; font-size:.88rem; line-height:1.5; }}
code, pre {{ font-family:ui-monospace,Menlo,monospace; font-size:.82rem; background:#F7F6F3; border:1px solid #EAEAEA; border-radius:4px; padding:.1rem .4rem; }}
pre {{ padding:.9rem; overflow:auto; white-space:pre-wrap; }}
.flag {{ background:#EDF3EC; color:#346538; border-radius:9999px; padding:.3rem 1rem; font-family:ui-monospace,Menlo,monospace; font-size:.85rem; display:inline-block; }}
.bad {{ color:#A33B3B; }}
</style></head><body><div class="box">{body}</div></body></html>"""
    return Response(html, status=status, mimetype="text/html")


@app.get("/healthz")
def healthz() -> Response:
    return Response("ok", mimetype="text/plain")


@app.get("/")
def index() -> Response:
    return _page(
        "<h1>Package takeover lab</h1>"
        "<p>This lab reproduces a dependency confusion incident against a "
        "fictional engineering org. The org resolves installs from a mixed "
        "feed where the highest version wins, names internal packages "
        "without reserving them upstream, and archives raw CI workspaces "
        "including credential files.</p>"
        "<h2>Surfaces</h2>"
        "<ul>"
        "<li>Public registry copy: <a href='/registry/company-utils'>/registry/company-utils</a></li>"
        "<li>Archived CI artifact: <a href='/evidence/ci-artifacts.npmrc'>/evidence/ci-artifacts.npmrc</a></li>"
        "<li>Publish contract: POST /publish with JSON fields name, version, token, install</li>"
        "<li>Takeover checker: GET /takeover-check</li>"
        "</ul>"
        "<h2>Canary policy</h2>"
        f"<p>The server-side installer runs every accepted hook inside the lab sandbox and requires each hook to ping <code>{CANARY_URL}</code> so executions can be attributed. Hooks are recorded as strings; nothing you submit is ever executed as code.</p>"
        "<p>Your objective: get company-utils above 1.0.0 published with your "
        "hook attached, then prove the install fired via the checker.</p>"
    )


@app.get("/registry/company-utils")
def registry_entry() -> Response:
    return jsonify(REGISTRY)


@app.get("/evidence/ci-artifacts.npmrc")
def evidence() -> Response:
    return Response(NPMRC_ARTIFACT, mimetype="text/plain")


@app.post("/publish")
def publish() -> Response:
    body = request.get_json(silent=True) or {}
    name = str(body.get("name", ""))
    version = str(body.get("version", ""))
    token = str(body.get("token", ""))
    hook = str(body.get("install", ""))

    if name != "company-utils":
        return jsonify({"accepted": False, "error": "unknown package name"}), 400
    if token != MAINTAINER_TOKEN:
        return jsonify({"accepted": False, "error": "publish token rejected"}), 401

    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", version)
    if not match or tuple(int(p) for p in match.groups()) <= (1, 0, 0):
        return jsonify(
            {
                "accepted": False,
                "error": "version must be semver and strictly greater than 1.0.0 to win resolution",
            }
        ), 400

    if CANARY_URL not in hook:
        return jsonify(
            {
                "accepted": False,
                "error": f"lab policy: install hooks must reference {CANARY_URL}",
            }
        ), 400

    state["takeover"] = {"name": name, "version": version, "hook": hook}
    try:
        with open("/tmp/canary-company-utils.json", "w") as fh:
            json.dump({"pkg": name, "version": version, "hook": hook}, fh)
    except OSError:
        pass

    return jsonify(
        {
            "accepted": True,
            "published": {"name": name, "version": version},
            "installer": {
                "resolved": "company-utils@" + version,
                "hook_recorded": True,
                "canary_written": "/tmp/canary-company-utils.json",
                "note": "simulated execution: hook stored as string, canary written by the lab itself",
            },
        }
    )


@app.get("/takeover-check")
def takeover_check() -> Response:
    record = state["takeover"]
    on_disk = os.path.exists("/tmp/canary-company-utils.json")
    if record is None or not on_disk:
        return _page(
            '<h1 class="bad">No takeover recorded</h1>'
            "<p>No canary execution is attributed to a hostile publish in "
            "this session. Publish a higher version first.</p>",
            status=404,
        )
    detail = json.dumps(record["hook"])
    return _page(
        "<h1>Takeover confirmed</h1>"
        "<p>The installer resolved company-utils@"
        f"{record['version']} from your publish claim and executed its "
        "declared install hook. The canary beacon fired from inside the "
        "build environment, which proves an attacker controlling this "
        "package would run code on every downstream build.</p>"
        f"<pre>{detail}</pre>"
        f"<span class='flag'>{FLAG}</span>"
        "<p>Remediation note: reserve internal names upstream, pin internal "
        "scopes to the private feed, scope and expire publish tokens, and "
        "scrub credentials out of archived CI artifacts.</p>"
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
