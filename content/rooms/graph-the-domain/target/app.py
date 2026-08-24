"""Domain graph collector and quiz: AD enumeration mapping sim. Room target only.

The graph below is fictional training data. It imitates the shape of a
BloodHound-style collection (nodes, edges, relationship names) so
learners can practice graph thinking without collecting data from any
real directory.
"""

import json
import os

from flask import Flask, Response, request
from markupsafe import escape

app = Flask(__name__)
FLAG = os.environ["ROOM_FLAG"]

GRAPH = {
    "meta": {
        "simulation": "Fictional BloodHound-style collection for training.",
        "realm": "LAB-SIM",
        "node_types": ["user", "group", "computer"],
        "edge_semantics": {
            "MemberOf": "user or subgroup belongs to group",
            "CanResetPassword": "user can force-reset the target user's password",
            "HasSession": "user is interactively signed in on computer",
            "AdminOn": "group members hold local admin on computer",
        },
    },
    "nodes": [
        {"id": "dana.reyes", "type": "user"},
        {"id": "marko.vukas", "type": "user"},
        {"id": "priya.nair", "type": "user"},
        {"id": "tom.hale", "type": "user"},
        {"id": "alice.wu", "type": "user"},
        {"id": "svc_backup", "type": "user"},
        {"id": "HELPDESK", "type": "group"},
        {"id": "SERVER OPERATORS", "type": "group"},
        {"id": "DOMAIN ADMINS", "type": "group"},
        {"id": "DC-01", "type": "computer"},
        {"id": "FILE-01", "type": "computer"},
        {"id": "WKST-09", "type": "computer"},
    ],
    "edges": [
        {"src": "priya.nair", "dst": "HELPDESK", "rel": "MemberOf"},
        {"src": "tom.hale", "dst": "HELPDESK", "rel": "MemberOf"},
        {"src": "marko.vukas", "dst": "SERVER OPERATORS", "rel": "MemberOf"},
        {"src": "alice.wu", "dst": "DOMAIN ADMINS", "rel": "MemberOf"},
        {"src": "dana.reyes", "dst": "svc_backup", "rel": "CanResetPassword"},
        {"src": "tom.hale", "dst": "svc_backup", "rel": "CanResetPassword"},
        {"src": "marko.vukas", "dst": "alice.wu", "rel": "CanResetPassword"},
        {"src": "dana.reyes", "dst": "WKST-09", "rel": "HasSession"},
        {"src": "alice.wu", "dst": "DC-01", "rel": "HasSession"},
        {"src": "svc_backup", "dst": "FILE-01", "rel": "HasSession"},
        {"src": "SERVER OPERATORS", "dst": "FILE-01", "rel": "AdminOn"},
        {"src": "DOMAIN ADMINS", "dst": "DC-01", "rel": "AdminOn"},
    ],
}

ANSWERS = {
    "q1": "6",
    "q2": "alice.wu",
    "q3": "2",
    "q4": "FILE-01",
    "q5": "SERVER OPERATORS",
}

QUESTIONS = [
    (
        "q1",
        "Counting every edge as traversable in either direction, what "
        "is the fewest number of edges on any path from user dana.reyes "
        "to group DOMAIN ADMINS? Answer with a number.",
    ),
    ("q2", "Which username is a member of DOMAIN ADMINS?"),
    (
        "q3",
        "How many distinct users hold a CanResetPassword edge over "
        "svc_backup? Answer with a number.",
    ),
    ("q4", "On which computer does svc_backup hold an interactive session?"),
    ("q5", "Which group's membership grants AdminOn rights over FILE-01?"),
]

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Lab Domain Collector</title>
<style>
body { background:#F7F6F3; font-family:Helvetica,Arial,sans-serif; display:flex; justify-content:center; padding-top:6vh; }
.box { background:#fff; border:1px solid #EAEAEA; border-radius:8px; padding:2.5rem; width:38rem; margin:.4rem; }
h1 { letter-spacing:-0.02em; font-size:1.35rem; margin-bottom:.8rem; }
input { width:100%%; padding:.5rem .75rem; margin:.35rem 0; border:1px solid #EAEAEA; border-radius:6px; }
button { background:#111; color:#fff; border:none; border-radius:6px; padding:.55rem 1rem; margin-top:.6rem; cursor:pointer; }
p, li { color:#787774; font-size:.92rem; }
label { display:block; margin-top:.9rem; color:#111; font-size:.92rem; }
.notice { border-left:3px solid #C9A227; padding-left:.8rem; }
.flag { background:#EDF3EC; color:#346538; border-radius:9999px; padding:.35rem 1rem; display:inline-block; }
code { font-family:ui-monospace,Menlo,monospace; background:#F7F6F3; padding:.1rem .3rem; border-radius:4px; }
.bad { color:#8A3A38; }
</style></head><body>%s</body></html>"""


def page(body: str):
    return PAGE % body


@app.get("/healthz")
def healthz():
    return "ok"


@app.get("/")
def home():
    return page(
        "<div class='box'><h1>Lab Domain Collector <small>(simulated)</small></h1>"
        f"<p class='notice'>Simulation notice: the directory graph served "
        "here is entirely fictional. No real domain was touched.</p>"
        "<p>This box imitates a graph collector for directory attack-path "
        "analysis. Fetch <a href='/collect/graph.json'>/collect/graph.json</a>, "
        "answer the five questions on the <a href='/quiz'>quiz page</a> from "
        "the data alone, and the full set unlocks your session token. The "
        "<a href='/about'>method notes</a> explain how paths are counted.</p></div>"
    )


@app.get("/about")
def about():
    return page(
        "<div class='box'><h1>Method notes</h1>"
        f"<p class='notice'>Simulation notice: fictional graph, real graph "
        "theory.</p>"
        "<ul>"
        "<li>Hop counts treat every edge as traversable in either "
        "direction, like walking the graph undirected. A hop is one edge.</li>"
        "<li>CanResetPassword means the source user can set the target "
        "user's password at will.</li>"
        "<li>AdminOn applies to every current member of the source group.</li>"
        "</ul></div>"
    )


@app.get("/collect/graph.json")
def collect():
    return Response(
        json.dumps(GRAPH, indent=2),
        mimetype="application/json",
        headers={"X-Simulation-Notice": "fictional training data"},
    )


@app.route("/quiz", methods=["GET", "POST"])
def quiz():
    if request.method == "GET":
        fields = "".join(
            f"<label>{escape(text)}</label>"
            f"<input name='{qid}' placeholder='your answer' autocomplete='off'>"
            for qid, text in QUESTIONS
        )
        return page(
            "<div class='box'><h1>Path quiz</h1>"
            f"<p class='notice'>Simulation notice: answers come only from "
            "/collect/graph.json.</p>"
            "<form method='post' action='/quiz'>"
            + fields
            + "<button type='submit'>Submit answer set</button></form></div>"
        )
    got = {}
    for qid, _text in QUESTIONS:
        raw = (request.form.get(qid) or "").strip().casefold()
        got[qid] = " ".join(raw.split())
    wrong = [qid for qid, want in ANSWERS.items() if got[qid] != want.casefold()]
    if not wrong:
        return page(
            "<div class='box'><h1>All five correct</h1>"
            "<p>You mapped the attack paths exactly. Session verification "
            "token:</p>"
            f"<span class='flag'>{FLAG}</span></div>"
        )
    listing = ", ".join(sorted(wrong))
    return page(
        f"<div class='box'><h1>Not yet</h1><p class='bad'>Recheck these: "
        f"{listing}.</p><p>Every answer must be derivable from the JSON "
        "graph; guesswork will not converge here.</p>"
        "<p><a href='/quiz'>Try again</a></p></div>"
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
