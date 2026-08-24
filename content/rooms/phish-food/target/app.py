"""Case file for the preserved phishing message. Room target only.

The .eml evidence is a static hand-written file; quiz answers are
constants and nothing here contacts a real mail system.
"""

import os
import pathlib

from flask import Flask, Response, request

app = Flask(__name__)
FLAG = os.environ["ROOM_FLAG"]

FROM_DOMAIN = "meridian-archive.com"
RETURN_PATH_DOMAIN = "mailer-relay-east.net"
LINK_DOMAIN = "mailpost-cdn.net"

EVIDENCE = pathlib.Path(__file__).parent / "evidence" / "mail.eml"

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Case 2026-08-14: quota phishing message</title>
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
<h1>Case 2026-08-14: quota phishing message</h1>
<p>The operations mailbox received a quota warning that nobody at the
service desk sent. The message was preserved raw as an .eml export,
headers and body exactly as delivered.</p>
<p>Evidence: <a href="/evidence/mail.eml">mail.eml</a> (plain text).</p>
<p>The indicator desk accepts three answers by POST to /quiz as JSON:
<code>from_domain</code> (the domain in the From header address),
<code>return_path_domain</code> (the domain in Return-Path), and
<code>link_domain</code> (the registrable domain of the URL in the
body). All three correct closes the case.</p>
</div>"""
    )


@app.get("/evidence/mail.eml")
def evidence():
    return Response(
        EVIDENCE.read_bytes(),
        mimetype="message/rfc822",
        headers={"Content-Disposition": "attachment; filename=mail.eml"},
    )


@app.post("/quiz")
def quiz():
    body = request.get_json(silent=True) or {}
    got = {
        "from_domain": str(body.get("from_domain", "")).strip().lower(),
        "return_path_domain": str(body.get("return_path_domain", "")).strip().lower(),
        "link_domain": str(body.get("link_domain", "")).strip().lower(),
    }
    want = {
        "from_domain": FROM_DOMAIN,
        "return_path_domain": RETURN_PATH_DOMAIN,
        "link_domain": LINK_DOMAIN,
    }
    wrong = sorted(k for k, v in want.items() if got[k] != v)
    if wrong:
        return {"result": "rejected", "wrong_keys": wrong}, 403
    return {"result": "accepted", "flag": FLAG}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, threaded=True)
