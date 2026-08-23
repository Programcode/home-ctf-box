"""Meridian webmail portal: SMTP VRFY enumeration simulation. Room target only."""

import os

from flask import Flask, Response, request
from markupsafe import escape

app = Flask(__name__)
FLAG = os.environ["ROOM_FLAG"]

TEMP_PASSWORD = "spring-meadow-42"

MAILBOXES = {
    "postmaster": {
        "gecos": "Meridian Mail Administrator",
        "messages": [
            {
                "from": "it-ops@meridianfreight.example",
                "subject": "Quarterly mailbox audit",
                "body": "All provisioned mailboxes were reviewed on schedule. "
                "Nothing to action. This is an automated notice.",
            },
            {
                "from": "postmaster-daemon@meridianfreight.example",
                "subject": "Autoresponder notice",
                "body": "The postmaster mailbox does not accept external mail. "
                "No flag is stored here; nice try though.",
            },
        ],
    },
    "reception": {
        "gecos": "Front Desk Rotation",
        "messages": [
            {
                "from": "facilities@meridianfreight.example",
                "subject": "Loading dock hours",
                "body": "Dock B closes at 16:00 on Fridays during August.",
            },
            {
                "from": "it-ops@meridianfreight.example",
                "subject": "Password rotation reminder",
                "body": "Shared temporary passwords expire after rotation week. "
                "Reception should not keep using theirs.",
            },
        ],
    },
    "jharper": {
        "gecos": "Jordan Harper, Platform Lead",
        "messages": [
            {
                "from": "noreply@meridianfreight.example",
                "subject": "Build 4471 green",
                "body": "Nightly regression passed. Coverage steady at 84 percent.",
            },
            {
                "from": "ops-review@meridianfreight.example",
                "subject": "Final architecture sign-off",
                "body": "Sign-off complete. Per policy the verification token is "
                f"recorded here until the archive job runs: {FLAG}",
            },
            {
                "from": "travel@meridianfreight.example",
                "subject": "Itinerary confirmation",
                "body": "Outbound confirmed for the Budapest depot visit.",
            },
        ],
    },
}

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Meridian MailGate</title>
<style>
body { background:#F7F6F3; font-family:Helvetica,Arial,sans-serif; display:flex; justify-content:center; padding-top:8vh; }
.box { background:#fff; border:1px solid #EAEAEA; border-radius:8px; padding:2rem; width:34rem; }
h1 { letter-spacing:-0.02em; font-size:1.35rem; margin-bottom:.5rem; }
h2 { font-size:1rem; margin-top:1.25rem; }
p, li { color:#787774; font-size:.9rem; }
code { background:#F7F6F3; padding:.1rem .35rem; border-radius:4px; font-size:.85rem; }
.sim { background:#FFF6E5; color:#8A6D3B; border:1px solid #EFE0B8; border-radius:6px; padding:.5rem .75rem; font-size:.82rem; }
</style></head><body>%s</body></html>"""

SIM_NOTICE = (
    "<p class='sim'>Simulation notice: this portal imitates a mail server's "
    "user-facing behavior over HTTP only. No SMTP daemon runs anywhere in "
    "this lab.</p>"
)


@app.get("/healthz")
def healthz():
    return "ok"


@app.get("/")
def home():
    return PAGE % (
        "<div class='box'><h1>Meridian MailGate</h1>" + SIM_NOTICE + "<h2>Operations status</h2>"
        "<p>The legacy VRFY compatibility endpoint is still enabled at "
        "<code>/api/vrfy?user=&lt;name&gt;</code>. It answers with code 250 and "
        "the account GECOS when a mailbox exists, and with code 550 when it "
        "does not. The helpdesk keeps it open because the label printer cannot "
        "speak anything else.</p>"
        "<p>Change ticket MR-2291, still open:</p>"
        "<ul><li>Mailbox provisioning migrated to the new directory.</li>"
        "<li>Until rotation week finishes, every staff mailbox uses the "
        "temporary password <code>spring-meadow-42</code>.</li>"
        "<li>Rotation completes next Tuesday. Do not ship this to prod docs.</li></ul>"
        "<p>Inboxes are served at <code>/inbox/&lt;mailbox&gt;</code> with HTTP "
        "basic auth.</p></div>"
    )


@app.get("/api/vrfy")
def vrfy():
    user = request.args.get("user", "")
    entry = MAILBOXES.get(user.lower())
    if user == "" or " " in user or "@" in user:
        return Response("501 5.5.4 Syntax error in parameters\n", mimetype="text/plain")
    if entry:
        return Response(f"250 2.1.5 {entry['gecos']}\n", mimetype="text/plain")
    return Response("550 5.1.1 Mailbox unavailable\n", mimetype="text/plain")


@app.get("/inbox/<name>")
def inbox(name):
    auth = request.authorization
    entry = MAILBOXES.get(name.lower())
    if entry is None:
        return PAGE % (
            "<div class='box'><h1>No such mailbox</h1>"
            "<p>VRFY would have told you this one first.</p></div>"
        )
    if auth is None or auth.username != name.lower() or auth.password != TEMP_PASSWORD:
        return Response(
            "401 Authentication required\n",
            401,
            {"WWW-Authenticate": 'Basic realm="Meridian MailGate"'},
        )
    items = "".join(
        f"<li><strong>{escape(m['subject'])}</strong><br>"
        f"from {escape(m['from'])}<br>{escape(m['body'])}</li>"
        for m in entry["messages"]
    )
    return PAGE % (
        f"<div class='box'><h1>Mailbox {escape(name)}</h1>" + SIM_NOTICE + f"<ol>{items}</ol></div>"
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
