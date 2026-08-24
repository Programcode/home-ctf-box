"""Build log spill case: a masked deploy token that two lines still leak. Room target only."""

import os

from flask import Flask, request
from markupsafe import escape

app = Flask(__name__)
FLAG = os.environ["ROOM_FLAG"]
DEPLOY_TOKEN = "ci-9f27d4c1ae83b650"

BUILD_LOG = """2026-08-19T02:14:07Z [runner-7] pipeline billing-api build #1234 started
2026-08-19T02:14:07Z [runner-7] mask policy: env secrets printed as base64 truncated to 20 of 28 chars; verify fingerprints keep last 4 raw chars; rotated tokens masked fully
2026-08-19T02:14:09Z [runner-7] step=checkout ref=main commit=8ac41f0
2026-08-19T02:14:12Z [runner-7] step=test suite=unit result=pass duration=3s
2026-08-19T02:14:38Z [runner-7] step=rotate-token old DEPLOY_TOKEN_B64=**** retired
2026-08-19T02:14:40Z [runner-7] step=deploy env=staging
2026-08-19T02:14:41Z [runner-7] exporting DEPLOY_TOKEN_B64=Y2ktOWYyN2Q0YzFhZTgz**** to environment
2026-08-19T02:14:42Z [runner-7] step=verify fingerprint ok for ****b650
2026-08-19T02:14:43Z [runner-7] POST /api/deploy?token=ci-**** -> 401 deploy rejected by control plane
2026-08-19T02:14:44Z [runner-7] retry policy: 3 attempts remaining
2026-08-19T02:15:01Z [runner-7] step=deploy attempt=2 result=accepted env=staging
2026-08-19T02:15:02Z [runner-7] step=notify channel=#deploys message=build green
2026-08-19T02:15:05Z [runner-7] pipeline finished status=success build=1234
"""

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Pipeline Spill</title>
<style>
body { background:#F7F6F3; font-family:Helvetica,Arial,sans-serif; display:flex; justify-content:center; padding-top:10vh; }
.box { background:#fff; border:1px solid #EAEAEA; border-radius:8px; padding:2.5rem; width:30rem; }
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
        '<div class="box"><h1>Case: build 1234 console output</h1>'
        "<p>The billing-api CI runner publishes raw console output to the shared "
        "evidence bucket after every build. Last night's green build shipped with "
        "the deploy token in scope of the log masker, and the on-call rotation "
        "wants to know whether masking actually held.</p>"
        "<p>Evidence: <a href='/evidence/build-1234.log'>build-1234.log</a>.</p>"
        "<p>Your job as the reviewer: decide if the token can be rebuilt from the "
        "log alone. If you manage it, replay it against "
        "<code>/api/deploy?token=...</code>. A token the control plane accepts "
        "proves the leak is real.</p></div>"
    )


@app.get("/evidence/build-1234.log")
def evidence() -> str:
    return BUILD_LOG


@app.get("/api/deploy")
def deploy() -> str:
    token = request.args.get("token", "")
    if token == DEPLOY_TOKEN:
        return page(
            '<div class="box"><h1>Deploy accepted</h1>'
            "<p>Control plane verified the token against staging release "
            "billing-api#1234. The masked log leaked a working secret.</p>"
            f"<span class='flag'>{FLAG}</span>"
            "<p>Remediation note: stop printing secrets in any form during "
            "builds, and treat every masked occurrence as compromised until "
            "rotated.</p></div>"
        )
    return page(
        '<div class="box"><h1 class="denied">Deploy rejected</h1>'
        f"<p>Token <code>{escape(token[:40])}</code> is not valid for this "
        "release.</p></div>"
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
