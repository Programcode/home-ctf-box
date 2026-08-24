"""HTTP mirror of the simulated SMB shares. Room target only."""

import os

from flask import Flask, Response, request

app = Flask(__name__)

SHARES = {
    "public": "/srv/samba/public",
    "dev$": "/srv/samba/dev$",
}
DEV_USER = os.environ.get("DEV_USER", "smbuser")
DEV_PASS = os.environ.get("DEV_PASS", "SpringSim26")

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>SIMFILE01 Share Mirror</title>
<style>
body { background:#F7F6F3; font-family:Helvetica,Arial,sans-serif; display:flex; justify-content:center; padding-top:8vh; }
.box { background:#fff; border:1px solid #EAEAEA; border-radius:8px; padding:2.5rem; width:34rem; }
h1 { letter-spacing:-0.02em; font-size:1.35rem; margin-bottom:.6rem; }
li { margin:.3rem 0; }
a { color:#111; }
p, small { color:#787774; font-size:.9rem; }
pre { background:#F7F6F3; border:1px solid #EAEAEA; border-radius:6px; padding:1rem; overflow:auto; font-size:.82rem; white-space:pre-wrap; }
</style></head><body>__BODY__</body></html>"""


def _page(body: str) -> str:
    return PAGE.replace("__BODY__", body)


def _check_dev_auth() -> bool:
    auth = request.authorization
    return bool(auth and auth.username == DEV_USER and auth.password == DEV_PASS)


def _listing(share: str) -> str:
    root = SHARES[share]
    items = []
    for name in sorted(os.listdir(root)):
        if os.path.isfile(os.path.join(root, name)):
            items.append(f"<li><a href='/files/{share}/{name}'>{name}</a></li>")
    label = "\\\\" + "SIMFILE01" + "\\" + share
    body = f"""
<div class="box">
<h1>Share mirror: {label}</h1>
<p>HTTP front-end for this training box's Samba shares, provided because
workstation images ship without an SMB client. On a real network the same
paths are reached as {label} with an SMB client.</p>
<ul>{"".join(items)}</ul>
<small>Read-only mirror. Files are also served over the real smb protocol
on port 445.</small>
</div>"""
    return _page(body)


@app.get("/healthz")
def healthz():
    return "ok"


@app.get("/")
def home():
    return _listing("public")


@app.get("/browse/<share>/")
def browse(share: str):
    if share not in SHARES:
        return _page("<div class='box'><h1>No such share</h1></div>"), 404
    if share == "dev$" and not _check_dev_auth():
        return Response(
            PAGE
            % (
                "<div class='box'><h1>Authentication required</h1>"
                "<p>This share is hidden from browse lists and requires"
                " valid credentials.</p></div>"
            ),
            401,
            {"WWW-Authenticate": 'Basic realm="SIMFILE01 dev"'},
        )
    return _listing(share)


@app.get("/files/<share>/<path:name>")
def get_file(share: str, name: str):
    if share not in SHARES:
        return _page("<div class='box'><h1>No such share</h1></div>"), 404
    if share == "dev$" and not _check_dev_auth():
        return Response(
            _page("<div class='box'><h1>Authentication required</h1></div>"),
            401,
            {"WWW-Authenticate": 'Basic realm="SIMFILE01 dev"'},
        )
    root = os.path.realpath(SHARES[share])
    target = os.path.realpath(os.path.join(root, name))
    if not target.startswith(root + os.sep) or not os.path.isfile(target):
        return _page("<div class='box'><h1>No such file</h1></div>"), 404
    with open(target, encoding="utf-8", errors="replace") as fh:
        content = fh.read()
    return _page(f"<div class='box'><h1>{name}</h1><pre>{content}</pre></div>")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
