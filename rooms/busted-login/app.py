from flask import Flask, request
from markupsafe import escape
import os
import sqlite3

app = Flask(__name__)
FLAG = os.environ["FLAG_1"]
DB_PATH = "/tmp/portal.db"

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Nimbus Portal</title>
<style>
body { background:#F7F6F3; font-family:'Helvetica Neue',Helvetica,Arial,sans-serif; display:flex; justify-content:center; padding-top:12vh; }
.box { background:#fff; border:1px solid #EAEAEA; border-radius:8px; padding:2.5rem; width:24rem; }
h1 { font-family:Georgia,serif; letter-spacing:-0.02em; font-size:1.4rem; margin-bottom:1rem; }
input { width:100%%; padding:.5rem .75rem; margin:.3rem 0; border:1px solid #EAEAEA; border-radius:6px; }
button { background:#111; color:#fff; border:none; border-radius:6px; padding:.5rem 1rem; margin-top:.6rem; width:100%%; cursor:pointer; }
button:hover { background:#333; }
p, li { color:#787774; font-size:.88rem; }
a { color:#111; }
pre { background:#F7F6F3; border:1px solid #EAEAEA; border-radius:6px; padding:1rem; overflow:auto; font-size:.8rem; }
.flag { background:#EDF3EC; color:#346538; border-radius:9999px; padding:.3rem 1rem; font-family:ui-monospace,Menlo,monospace; font-size:.85rem; display:inline-block; }
</style></head><body>%s</body></html>"""


def init():
    con = sqlite3.connect(DB_PATH)
    con.executescript("CREATE TABLE IF NOT EXISTS users(username TEXT, password TEXT)")
    if not con.execute("SELECT 1 FROM users LIMIT 1").fetchone():
        con.execute("INSERT INTO users VALUES ('admin','s3cr3t_pa55')")
        con.execute("INSERT INTO users VALUES ('guest','guest123')")
    con.commit()
    con.close()


init()


@app.route("/")
def home():
    return (
        PAGE
        % """<div class="box">
<h1>Nimbus Portal</h1>
<p>Employee sign-in. Guests may browse the canteen menu.</p>
<form method="post" action="/login">
<input name="username" placeholder="username" autocomplete="off">
<input name="password" type="password" placeholder="password">
<button type="submit">Sign in</button>
</form>
</div>"""
    )


@app.route("/login", methods=["POST"])
def login():
    u = request.form.get("username", "")
    p = request.form.get("password", "")
    con = sqlite3.connect(DB_PATH)
    q = f"SELECT username FROM users WHERE username='{u}' AND password='{p}'"
    try:
        row = con.execute(q).fetchone()
        err = None
    except Exception as exc:
        row, err = None, str(exc)
    con.close()
    if err is not None:
        return (
            PAGE
            % f'<div class="box"><h1>Query error</h1><pre>{escape(err)}</pre></div>'
        )
    if row is None:
        return (
            PAGE
            % '<div class="box"><h1>Access denied</h1><p>Bad credentials. <a href="/">Try again</a></p></div>'
        )
    who = row[0]
    if who == "admin":
        return PAGE % (
            '<div class="box"><h1>Welcome, admin</h1>'
            f"<p>Your session reward:</p><span class='flag'>{FLAG}</span></div>"
        )
    return (
        PAGE
        % f'<div class="box"><h1>Welcome, {escape(who)}</h1><p>Nothing interesting for guests here.</p></div>'
    )


from markupsafe import escape

app.run(host="0.0.0.0", port=5000)
