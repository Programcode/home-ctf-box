import os

from flask import Flask, redirect, request, session
from markupsafe import escape
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.secret_key = "dev-secret-idor"
FLAG = os.environ["FLAG_6"]

USERS = {
    "guest": generate_password_hash("guest123"),
    "admin": generate_password_hash("correct-horse-battery"),
}

INVOICES = {
    101: {"owner": "guest", "amount": "120.00", "note": "Hosting"},
    102: {"owner": "guest", "amount": "48.50", "note": "Domain renewal"},
    777: {"owner": "admin", "amount": "9999.00", "note": FLAG},
}

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>BillVault</title>
<style>
body { background:#F7F6F3; font-family:'Helvetica Neue',Helvetica,Arial,sans-serif; display:flex; justify-content:center; padding-top:12vh; }
.box { background:#fff; border:1px solid #EAEAEA; border-radius:8px; padding:2.5rem; width:26rem; }
h1 { font-family:Georgia,serif; letter-spacing:-0.02em; font-size:1.4rem; margin-bottom:.5rem; }
p { color:#787774; font-size:.88rem; }
li { margin:.4rem 0; }
a { color:#111; }
input { width:100%; padding:.5rem .75rem; border:1px solid #EAEAEA; border-radius:6px; font-size:.9rem; margin-top:.4rem; }
button { background:#111; color:#fff; border:none; border-radius:6px; padding:.5rem 1.2rem; margin-top:.8rem; cursor:pointer; }
button:hover { background:#333; }
.err { color:#B3261E; margin-top:.8rem; }
</style></head><body>__BODY__</body></html>"""

LOGIN_FORM = """<div class="box">
<h1>BillVault</h1>
<p>Billing portal. Sign in to view your invoices.</p>
<form method="post" action="/login">
<input name="username" placeholder="Username" autocomplete="off">
<input name="password" type="password" placeholder="Password">
<button type="submit">Sign in</button>
</form>
__MSG__
</div>"""


@app.route("/")
def index():
    return PAGE.replace("__BODY__", LOGIN_FORM.replace("__MSG__", ""))


@app.route("/login", methods=["POST"])
def login():
    username = request.form.get("username", "")
    password = request.form.get("password", "")
    stored = USERS.get(username)
    if stored is None or not check_password_hash(stored, password):
        body = LOGIN_FORM.replace("__MSG__", '<p class="err">Invalid credentials</p>')
        return PAGE.replace("__BODY__", body), 401
    session["user"] = username
    return redirect("/invoices")


@app.route("/invoices")
def invoices():
    user = session.get("user")
    if not user:
        return redirect("/")
    rows = "".join(
        f'<li><a href="/invoice/{iid}">Invoice #{iid}</a> &mdash; {escape(inv["amount"])} EUR</li>'
        for iid, inv in sorted(INVOICES.items())
        if inv["owner"] == user
    )
    body = (
        '<div class="box"><h1>BillVault</h1>'
        f"<p>Invoices for {escape(user)}:</p>"
        f"<ul>{rows}</ul></div>"
    )
    return PAGE.replace("__BODY__", body)


@app.route("/invoice/<int:inv_id>")
def invoice(inv_id):
    if not session.get("user"):
        return redirect("/")
    inv = INVOICES.get(inv_id)
    if inv is None:
        body = '<div class="box"><h1>BillVault</h1><p>No such invoice.</p></div>'
        return PAGE.replace("__BODY__", body)
    body = (
        '<div class="box"><h1>BillVault</h1>'
        f"<p>Invoice #{inv_id}</p>"
        f"<p>Owner: {escape(inv['owner'])}</p>"
        f"<p>Amount: {escape(inv['amount'])} EUR</p>"
        f"<p>Note: {escape(inv['note'])}</p></div>"
    )
    return PAGE.replace("__BODY__", body)


app.run(host="0.0.0.0", port=5000)
