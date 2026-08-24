"""Case file for the workstation memory capture. Room target only.

Both evidence files are static synthetic text; the report answers are
constants and nothing here analyzes a real memory image.
"""

import os
import pathlib

from flask import Flask, Response, request

app = Flask(__name__)
FLAG = os.environ["ROOM_FLAG"]

PROCESS_PATH = "/tmp/.cache/fontconfig/gnome-calc-helper"
PARENT_PID = "3491"
C2_DOMAIN = "updates-eastward-cdn.net"

EVIDENCE_DIR = pathlib.Path(__file__).parent / "evidence"

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Case 2026-08-16: workstation-7 memory capture</title>
<style>
body { background:#F7F6F3; font-family:Helvetica,Arial,sans-serif; display:flex; justify-content:center; padding-top:12vh; }
.box { background:#fff; border:1px solid #EAEAEA; border-radius:8px; padding:2.5rem; width:34rem; }
h1 { letter-spacing:-0.02em; font-size:1.35rem; margin-bottom:1rem; }
p, li { color:#787774; font-size:.9rem; line-height:1.55; }
code { background:#F7F6F3; padding:.1rem .35rem; border-radius:4px; font-size:.85rem; }
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
<h1>Case 2026-08-16: workstation-7 memory capture</h1>
<p>Workstation-7 behaved strangely for two days before it was
reimaged. The imaging rig captured memory first and the lab reduced the
capture to two readable artifacts.</p>
<p>Evidence:
<a href="/evidence/processes.txt">processes.txt</a> (ps-style listing)
and <a href="/evidence/strings-excerpt.txt">strings-excerpt.txt</a>
(printable strings from the capture).</p>
<p>The lab desk accepts three findings by POST to /report as JSON:
<code>process_path</code> (full path of the injected process),
<code>parent_pid</code>, and <code>c2_domain</code>. All three correct
closes the case.</p>
</div>"""
    )


@app.get("/evidence/processes.txt")
def processes():
    return Response(
        (EVIDENCE_DIR / "processes.txt").read_bytes(),
        mimetype="text/plain",
        headers={"Content-Disposition": "attachment; filename=processes.txt"},
    )


@app.get("/evidence/strings-excerpt.txt")
def strings_excerpt():
    return Response(
        (EVIDENCE_DIR / "strings-excerpt.txt").read_bytes(),
        mimetype="text/plain",
        headers={"Content-Disposition": "attachment; filename=strings-excerpt.txt"},
    )


@app.post("/report")
def report():
    body = request.get_json(silent=True) or {}
    got = {
        "process_path": str(body.get("process_path", "")).strip(),
        "parent_pid": str(body.get("parent_pid", "")).strip(),
        "c2_domain": str(body.get("c2_domain", "")).strip().lower(),
    }
    want = {
        "process_path": PROCESS_PATH,
        "parent_pid": PARENT_PID,
        "c2_domain": C2_DOMAIN,
    }
    wrong = sorted(k for k, v in want.items() if got[k] != v)
    if wrong:
        return {"result": "rejected", "wrong_keys": wrong}, 403
    return {"result": "accepted", "flag": FLAG}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, threaded=True)
