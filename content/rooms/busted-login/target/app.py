"""Nimbus portal: deliberately vulnerable to SQL injection. Room target only."""

import os
import sqlite3

from flask import Flask, request
from markupsafe import escape

app = Flask(__name__)
FLAG = os.environ["ROOM_FLAG"]
DB_PATH = "/tmp/portal.db"

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Nimbus Portal</title>
<style>
body { background:#F7F6F3; font-family:Helvetica,Arial,sans-serif; display:flex; justify-content:center; padding-top:12vh; }
.box { background:#fff; border:1px solid #EAEAEA; border-radius:8px; padding:2.5rem; width:26rem; }
h1 { letter-spacing:-0.02em; font-size:1.4rem; margin-bottom:1rem; }
input { width:100%%; padding:.5rem .75rem; margin:.3rem 0; border:1px solid #EAEAEA; border-radius:6px; }
button { background:#111; color:#fff; border:none; border-radius:6px; padding:.55rem 1rem; margin-top:.6rem; width:100%%; cursor:pointer; }
p, li { color:#787774; font-size:.9rem; }
pre { background:#F7F6F3; border:1px solid #EAEAEA; border-radius:6px; padding:1rem; overflow:auto; font-size:.82rem; }
.flag { background:#EDF3EC; color:#346538; border-radius:9999px; padding:.35rem 1rem; display:inline-block; }
</style></head><body>%s</body></html>"""


def db():
    con = sqlite3.connect(DB_PATH)
    con.execute("CREATE TABLE IF NOT EXISTS users(username TEXT, password TEXT)")
    if not con.execute("SELECT 1 FROM users LIMIT 1").fetchone():
        con.execute("INSERT INTO users VALUES ('admin','7f3d91c2aa')")
        con.execute("INSERT INTO users VALUES ('guest','welcome')")
        con.commit()
    return con


@app.get("/healthz")
def healthz():
    return "ok"


@app.get("/")
def home():
    return (
        PAGE
        % """
<div class="box">
<h1>Nimbus Portal</h1>
<p>Employee sign-in. Guests may browse the canteen menu.</p>
<form method="post" action="/login">
<input name="username" placeholder="username" autocomplete="off">
<input name="password" type="password" placeholder="password">
<button type="submit">Sign in</button>
</form>
</div>"""
    )


@app.post("/login")
def login():
    username = request.form.get("username", "")
    password = request.form.get("password", "")
    con = db()
    # The intern's query: values are glued straight into the SQL string.
    query = f"SELECT username FROM users WHERE username = '{username}' AND password = '{password}'"
    try:
        row = con.execute(query).fetchone()
    except sqlite3.OperationalError as exc:
        con.close()
        return PAGE % (
            f"<div class='box'><h1>Sign-in failed</h1>"
            f"<pre>{escape(str(exc))}</pre>"
            "<p>The error above is real SQLite output.</p></div>"
        )
    con.close()
    if row:
        return PAGE % (
            f"<div class='box'><h1>Welcome back, {escape(row[0])}</h1>"
            "<p>Your session is ready. Here is your onboarding token:</p>"
            f"<span class='flag'>{FLAG}</span></div>"
        )
    return PAGE % (
        "<div class='box'><h1>Sign-in failed</h1><p>Unknown username or wrong password.</p></div>"
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
