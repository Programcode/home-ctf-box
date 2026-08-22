from contextlib import closing
from flask import Flask, jsonify, redirect, render_template_string, request, session
from werkzeug.security import check_password_hash, generate_password_hash
import os
import secrets
import sqlite3

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or secrets.token_hex(32)

DB_DIR = "/data"
DB_PATH = os.path.join(DB_DIR, "ctf.db")

FLAGS = {
    1: os.environ.get("FLAG_1", ""),
    2: os.environ.get("FLAG_2", ""),
    3: os.environ.get("FLAG_3", ""),
    4: os.environ.get("FLAG_4", ""),
    5: os.environ.get("FLAG_5", ""),
    6: os.environ.get("FLAG_6", ""),
    7: os.environ.get("FLAG_7", ""),
    8: os.environ.get("FLAG_8", ""),
    9: os.environ.get("FLAG_9", ""),
    10: os.environ.get("FLAG_10", ""),
    11: os.environ.get("FLAG_11", ""),
    12: os.environ.get("FLAG_12", ""),
    13: os.environ.get("FLAG_13", ""),
    14: os.environ.get("FLAG_14", ""),
    15: os.environ.get("FLAG_15", ""),
    16: os.environ.get("FLAG_16", ""),
    17: os.environ.get("FLAG_17", ""),
    18: os.environ.get("FLAG_18", ""),
    19: os.environ.get("FLAG_19", ""),
    20: os.environ.get("FLAG_20", ""),
}

CHALLENGES = [
    {
        "id": 1,
        "name": "Busted Login",
        "points": 100,
        "url": "http://<host>:8081  POST /login",
        "brief": "Nimbus Corp employee portal. The intern wrote the SQL query by hand.",
        "hint": "Whatever you type lands inside a string-concatenated SQL statement.",
    },
    {
        "id": 2,
        "name": "Nosy Files",
        "points": 150,
        "url": "http://<host>:8082  GET /download?name=",
        "brief": "Internal document server. It checks that paths do not start with a slash, and stops there.",
        "hint": "How does the server turn ?name= into a filesystem path?",
    },
    {
        "id": 3,
        "name": "Ping of Doom",
        "points": 200,
        "url": "http://<host>:8083  POST /ping",
        "brief": "Network diagnostics tool. It really, really trusts your input.",
        "hint": "Whatever you type ends up inside a shell command.",
    },
    {
        "id": 4,
        "name": "SSTI Greeting",
        "points": 150,
        "url": "http://<host>:8084  POST /greet",
        "brief": "A friendly greeting card generator. The greeting string goes straight into the template engine.",
        "hint": "Jinja evaluates expressions in double curly braces.",
    },
    {
        "id": 5,
        "name": "Token Forger",
        "points": 250,
        "url": "http://<host>:8085  GET /admin (Bearer token)",
        "brief": "An API gateway with hand-rolled JWT verification. The algorithm comes from the token itself.",
        "hint": "alg:none means exactly what it says.",
    },
    {
        "id": 6,
        "name": "IDOR Invoices",
        "points": 125,
        "url": "http://<host>:8086  GET /invoice/<id>",
        "brief": "Billing portal. Your invoices are yours; the check that should enforce that is missing.",
        "hint": "Invoice numbers are small integers. Try a few you do not own.",
    },
    {
        "id": 7,
        "name": "Open Panels",
        "points": 50,
        "url": "http://<host>:8087  GET /debug",
        "brief": "Someone left the debug panel reachable in production. Happens to the best of us.",
        "hint": "Just browse to /debug.",
    },
    {
        "id": 8,
        "name": "Cookie Shapeshifter",
        "points": 100,
        "url": "http://<host>:8088  GET /admin-panel",
        "brief": "Your identity is a base64 cookie. Base64 decodes both ways.",
        "hint": "Decode the profile cookie, edit the role, encode it back.",
    },
    {
        "id": 9,
        "name": "Regex Doom",
        "points": 125,
        "url": "http://<host>:8089  POST /unlock",
        "brief": "The vault compares your code against the secret using a pattern match. Your input is the pattern.",
        "hint": "Which regex matches every string?",
    },
    {
        "id": 10,
        "name": "Mass Assign",
        "points": 150,
        "url": "http://<host>:8090  POST /profile?u=",
        "brief": "Profile updates copy every JSON key into the user record. Every key.",
        "hint": "Send a key the form never showed you.",
    },
    {
        "id": 11,
        "name": "XXE Importer",
        "points": 225,
        "url": "http://<host>:8091  POST /import",
        "brief": "An XML import endpoint with entity processing left on.",
        "hint": "Define a SYSTEM entity pointing at file:///flag.txt.",
    },
    {
        "id": 12,
        "name": "Pickle Jar",
        "points": 275,
        "url": "http://<host>:8092  POST /load",
        "brief": "Session state is a base64 pickle. The server trusts it completely. It should not.",
        "hint": "Craft a pickle whose __reduce__ reads /flag.txt. python3 on your side is enough.",
    },
    {
        "id": 13,
        "name": "Trusted Proxy",
        "points": 75,
        "url": "http://<host>:8093  GET /internal",
        "brief": "The admin panel trusts X-Forwarded-For to know where you are from.",
        "hint": "You can write that header yourself.",
    },
    {
        "id": 14,
        "name": "Wrong Method",
        "points": 75,
        "url": "http://<host>:8094  /admin-console",
        "brief": "GET is blocked because browsers use GET. The other verbs are apparently fine.",
        "hint": "curl -X PUT.",
    },
    {
        "id": 15,
        "name": "Open Closet",
        "points": 50,
        "url": "http://<host>:8095  GET /backups/",
        "brief": "The backups directory listing is enabled. The dumps are interesting.",
        "hint": "Read the dump file from the listing.",
    },
    {
        "id": 16,
        "name": "Predictable Reset",
        "points": 175,
        "url": "http://<host>:8096  POST /forgot, GET /reset",
        "brief": "Password reset tokens are derived from the username and the clock. You have both.",
        "hint": "md5(username + ':' + unix_time / 600).",
    },
    {
        "id": 17,
        "name": "Double Trouble",
        "points": 150,
        "url": "http://<host>:8097  GET /checkout",
        "brief": "The checkout validates one discount parameter and calculates with another. Send both.",
        "hint": "Duplicate the discount parameter; validation reads the first, math reads the last.",
    },
    {
        "id": 18,
        "name": "Fetch Boy",
        "points": 200,
        "url": "http://<host>:8098  GET /fetch?url=",
        "brief": "A URL preview service. There is an internal-only endpoint on localhost:9001 of the same box.",
        "hint": "Make the server request itself.",
    },
    {
        "id": 19,
        "name": "Union Vault",
        "points": 225,
        "url": "http://<host>:8099  GET /products?q=",
        "brief": "Product search with string-built SQL. Two columns are selected; make your own rows.",
        "hint": "UNION SELECT needs matching column count. There is a vault table.",
    },
    {
        "id": 20,
        "name": "Brace Yourself",
        "points": 125,
        "url": "http://<host>:8100  GET /welcome?name=",
        "brief": "Your name is inserted into a format string before formatting happens. The context has secrets.",
        "hint": "{flag} is a valid field reference.",
    },
]
POINTS = {c["id"]: c["points"] for c in CHALLENGES}
NAMES = {c["id"]: c["name"] for c in CHALLENGES}
TOTAL = sum(POINTS.values())

STYLE = """
* { box-sizing:border-box; margin:0; padding:0; }
body { background:#F7F6F3; color:#111; font-family:'Helvetica Neue',Helvetica,Arial,sans-serif; line-height:1.6; }
.wrap { max-width:56rem; margin:0 auto; padding:3rem 1.5rem 5rem; }
nav { display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid #EAEAEA; padding-bottom:1rem; margin-bottom:2.5rem; }
nav a { color:#111; text-decoration:none; margin-left:1rem; font-size:.9rem; }
.sub { color:#787774; font-size:.95rem; }
h1 { font-family:Georgia,'Times New Roman',serif; letter-spacing:-0.03em; font-size:2rem; margin-bottom:.25rem; }
h2 { font-size:1.05rem; margin:2rem 0 1rem; letter-spacing:-0.01em; }
.card { background:#fff; border:1px solid #EAEAEA; border-radius:8px; padding:1.5rem; margin-bottom:1.25rem; }
.ch-name { font-weight:600; display:flex; gap:.75rem; align-items:center; flex-wrap:wrap; }
.pill { font-size:.68rem; letter-spacing:.05em; text-transform:uppercase; border-radius:9999px; padding:.15rem .6rem; }
.open { background:#FBF3DB; color:#956400; }
.done { background:#EDF3EC; color:#346538; }
.brief { color:#787774; font-size:.92rem; margin-top:.35rem; }
.meta { font-family:ui-monospace,'SF Mono',Menlo,monospace; font-size:.8rem; color:#787774; margin-top:.35rem; }
input[type=text], input[type=password] { width:100%; max-width:22rem; padding:.55rem .75rem; border:1px solid #EAEAEA; border-radius:6px; font-size:.95rem; background:#fff; }
button { background:#111; color:#fff; border:none; border-radius:6px; padding:.55rem 1.1rem; font-size:.9rem; cursor:pointer; margin-top:.5rem; }
button:hover { background:#333; }
button:active { transform:scale(.98); }
table { width:100%; border-collapse:collapse; font-size:.92rem; }
th { text-align:left; color:#787774; font-weight:500; font-size:.78rem; text-transform:uppercase; letter-spacing:.05em; padding:.5rem .75rem; border-bottom:1px solid #EAEAEA; }
td { padding:.6rem .75rem; border-bottom:1px solid #EAEAEA; }
.msg { padding:.75rem 1rem; border-radius:8px; margin-bottom:1.25rem; font-size:.92rem; }
.ok { background:#EDF3EC; color:#346538; }
.err { background:#FDEBEC; color:#9F2F2D; }
details summary { font-size:.85rem; color:#787774; cursor:pointer; margin-top:.5rem; }
footer { margin-top:3rem; border-top:1px solid #EAEAEA; padding-top:1rem; }
"""

LAYOUT = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>home_ctf_box</title>
<style>{{ style|safe }}</style>
</head>
<body>
<div class="wrap">
<nav>
<strong>home_ctf_box</strong>
<span class="sub">
{% if uid %}{{ uname|e }} <a href="/logout">log out</a>{% else %}<a href="/login">log in</a> <a href="/register">register</a>{% endif %}
</span>
</nav>
{{ body|safe }}
<footer class="sub">LAN only. These services are vulnerable on purpose. Never port-forward them.</footer>
</div>
</body>
</html>"""

HOME_BODY = """
{% if msg %}<div class="msg {{ kind }}">{{ msg|e }}</div>{% endif %}
<h1>Break your own stuff.</h1>
<p class="sub" style="margin-bottom:2rem;">Three rooms, one scoreboard. Exploit the service, grab its flag, paste it below.</p>
<div class="card">
<form method="post" action="/submit">
<input type="text" name="flag" placeholder="FLAG{...}" autocomplete="off" style="margin-bottom:.25rem;">
<br><button type="submit">Submit flag</button>
</form>
</div>
<h2>Challenges</h2>
{% for c in challenges %}
<div class="card">
<div class="ch-name">{{ c.name }} <span class="pill {{ 'done' if c.solved else 'open' }}">{{ 'solved' if c.solved else 'open' }}</span></div>
<div class="brief">{{ c.brief }}</div>
<div class="meta">{{ c.url }}</div>
<details><summary>hint</summary><div class="brief">{{ c.hint }}</div></details>
</div>
{% endfor %}
<h2>Scoreboard</h2>
<div class="card" style="padding:0;">
<table>
<tr><th>#</th><th>player</th><th>solved</th><th>score</th></tr>
{% for r in board %}
<tr><td>{{ loop.index }}</td><td>{{ r.username|e }}</td><td>{{ r.solved }}/{{ total }}</td><td>{{ r.score }}</td></tr>
{% endfor %}
{% if not board %}<tr><td colspan="4" class="sub">no players yet</td></tr>{% endif %}
</table>
</div>
"""

AUTH_BODY = """
{% if msg %}<div class="msg {{ kind }}">{{ msg|e }}</div>{% endif %}
<h1>Welcome.</h1>
<p class="sub" style="margin-bottom:2rem;">Pick a handle and start breaking things.</p>
<div class="card">
<form method="post" action="/register">
<label style="font-size:.9rem;color:#787774;">Register</label><br>
<input type="text" name="username" placeholder="username" autocomplete="off"><br>
<input type="password" name="password" placeholder="password"><br>
<button type="submit">Create account</button>
</form>
</div>
<div class="card">
<form method="post" action="/login">
<label style="font-size:.9rem;color:#787774;">Log in</label><br>
<input type="text" name="username" placeholder="username" autocomplete="off"><br>
<input type="password" name="password" placeholder="password"><br>
<button type="submit">Log in</button>
</form>
</div>
"""


def db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def init_db():
    os.makedirs(DB_DIR, exist_ok=True)
    with closing(db()) as con:
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                pw TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS solves (
                user_id INTEGER NOT NULL,
                challenge_id INTEGER NOT NULL,
                ts DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, challenge_id)
            );
            """
        )
        con.commit()


init_db()


def page(body_tpl, **ctx):
    body = render_template_string(body_tpl, **ctx)
    return render_template_string(
        LAYOUT,
        style=STYLE,
        body=body,
        uid=session.get("uid"),
        uname=session.get("uname", ""),
    )


def board_rows(con):
    rows = []
    for u in con.execute("SELECT id, username FROM users").fetchall():
        solved = {
            r["challenge_id"]
            for r in con.execute(
                "SELECT challenge_id FROM solves WHERE user_id = ?", (u["id"],)
            ).fetchall()
        }
        score = sum(POINTS[c] for c in solved)
        rows.append({"username": u["username"], "solved": len(solved), "score": score})
    rows.sort(key=lambda r: (-r["score"], r["username"]))
    return rows


@app.route("/healthz")
def healthz():
    return "ok"


@app.route("/")
def index():
    with closing(db()) as con:
        if not session.get("uid"):
            return page(AUTH_BODY, msg=request.args.get("m"), kind="err")
        uid = session["uid"]
        solved = {
            r["challenge_id"]
            for r in con.execute(
                "SELECT challenge_id FROM solves WHERE user_id = ?", (uid,)
            ).fetchall()
        }
        challenges = [dict(c, solved=c["id"] in solved) for c in CHALLENGES]
        board = board_rows(con)
    return page(
        HOME_BODY,
        msg=None,
        kind=None,
        challenges=challenges,
        board=board,
        total=len(CHALLENGES),
    )


@app.route("/register", methods=["POST"])
def register():
    uname = (request.form.get("username") or "").strip()
    pw = request.form.get("password") or ""
    if not (3 <= len(uname) <= 24) or len(pw) < 4:
        return "bad username or password", 400
    try:
        with closing(db()) as con:
            cur = con.execute(
                "INSERT INTO users (username, pw) VALUES (?, ?)",
                (uname, generate_password_hash(pw)),
            )
            con.commit()
            uid = cur.lastrowid
    except sqlite3.IntegrityError:
        return "username taken", 400
    session["uid"] = uid
    session["uname"] = uname
    return redirect("/")


@app.route("/login", methods=["POST"])
def login():
    uname = (request.form.get("username") or "").strip()
    pw = request.form.get("password") or ""
    with closing(db()) as con:
        row = con.execute(
            "SELECT id, username, pw FROM users WHERE username = ?", (uname,)
        ).fetchone()
    if row is None or not check_password_hash(row["pw"], pw):
        return "bad credentials", 400
    session["uid"] = row["id"]
    session["uname"] = row["username"]
    return redirect("/")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


@app.route("/submit", methods=["POST"])
def submit():
    if not session.get("uid"):
        return "not logged in", 401
    flag = (request.form.get("flag") or "").strip()
    matched = [cid for cid, f in FLAGS.items() if f and f == flag]
    if not matched:
        return jsonify(ok=False, error="nope")
    cid = matched[0]
    uid = session["uid"]
    with closing(db()) as con:
        already = con.execute(
            "SELECT 1 FROM solves WHERE user_id = ? AND challenge_id = ?", (uid, cid)
        ).fetchone()
        if already:
            return jsonify(ok=True, repeat=True, message=f"already got {NAMES[cid]}")
        con.execute(
            "INSERT INTO solves (user_id, challenge_id) VALUES (?, ?)", (uid, cid)
        )
        con.commit()
    return jsonify(ok=True, challenge=NAMES[cid], points=POINTS[cid])


@app.route("/api/scoreboard")
def api_scoreboard():
    with closing(db()) as con:
        return jsonify(board_rows(con))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
