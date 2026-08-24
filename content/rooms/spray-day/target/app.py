"""Harborview staff portal: lockout-aware password spraying lab. Room target only.

Every account, mailbox, and password in this app is fictional training
data. The lockout counter exists to reward spraying discipline: one
attempt per account per candidate, never three strikes on one name.
"""

import os
import time

from flask import Flask, request
from markupsafe import escape

app = Flask(__name__)
FLAG = os.environ["ROOM_FLAG"]
SHARED_PASSWORD = "RiverbankOtter07"
LOCKOUT_AFTER = 3
LOCKOUT_SECONDS = 90

# (display name, title) for every staff entry; membership in VALID
# decides whether the mailbox and login actually exist.
STAFF = [
    ("Dana Reyes", "Operations lead", "dana.reyes@harborview.example", True),
    ("Marko Vukas", "Database admin", "marko.vukas@harborview.example", True),
    ("Priya Nair", "Finance analyst", "priya.nair@harborview.example", True),
    ("Tom Hale", "Field technician", "tom.hale@harborview.example", True),
    ("Alice Wu", "Compliance officer", "alice.wu@harborview.example", True),
    ("Helpdesk", "Shared service desk", "helpdesk@harborview.example", True),
    ("Facilities", "Building management", "facilities@harborview.example", True),
    ("Nora Stanton", "Sales rep", "n.stanton@harborview.example", False),
    ("Louis Ferrand", "Recruiter", "l.ferrand@harborview.example", False),
    ("Oleg Petrov", "Contractor", "o.petrov@harborview.example", False),
    ("Keeley Dunmore", "Marketing", "k.dunmore@harborview.example", False),
]
MAILBOX = {email: name for name, _title, email, valid in STAFF if valid}

failures: dict[str, int] = {}
locked_until: dict[str, float] = {}

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Harborview Staff Portal</title>
<style>
body { background:#F7F6F3; font-family:Helvetica,Arial,sans-serif; display:flex; justify-content:center; padding-top:8vh; }
.box { background:#fff; border:1px solid #EAEAEA; border-radius:8px; padding:2.5rem; width:36rem; margin:.5rem; }
h1 { letter-spacing:-0.02em; font-size:1.35rem; margin-bottom:.8rem; }
table { border-collapse:collapse; width:100%%; margin:1rem 0; font-size:.9rem; }
td, th { border-top:1px solid #EAEAEA; padding:.5rem .4rem; text-align:left; }
input { width:100%%; padding:.5rem .75rem; margin:.3rem 0; border:1px solid #EAEAEA; border-radius:6px; }
button { background:#111; color:#fff; border:none; border-radius:6px; padding:.55rem 1rem; margin-top:.4rem; cursor:pointer; }
p, li { color:#787774; font-size:.92rem; }
.notice { border-left:3px solid #C9A227; padding-left:.8rem; }
.flag { background:#EDF3EC; color:#346538; border-radius:9999px; padding:.35rem 1rem; display:inline-block; }
code { font-family:ui-monospace,Menlo,monospace; background:#F7F6F3; padding:.1rem .3rem; border-radius:4px; }
</style></head><body>%s</body></html>"""


def page(body: str):
    return PAGE % body


@app.get("/healthz")
def healthz():
    return "ok"


@app.get("/")
def home():
    return page(
        "<div class='box'><h1>Harborview Staff Portal <small>(simulated)</small></h1>"
        f"<p class='notice'>Simulation notice: every person, mailbox, and "
        "password on this site is fictional training data. Nothing here "
        "touches a real identity provider.</p>"
        "<p>This portal signs staff in to the intranet. An unusually strict "
        "<a href='/policy'>lockout policy</a> protects the sign-in form, "
        "the <a href='/directory'>staff directory</a> lists everybody the "
        "company is proud of, and facilities keeps a running "
        "<a href='/memo'>memo board</a>. Forgot your password? The "
        "reset form below will tell you whether a reset was queued.</p>"
        "<form method='post' action='/forgot'>"
        "<input name='email' placeholder='work email' autocomplete='off'>"
        "<button type='submit'>Request reset</button></form></div>"
    )


@app.get("/policy")
def policy():
    return page(
        "<div class='box'><h1>Sign-in and lockout policy</h1>"
        f"<p class='notice'>Simulation notice: this page is training "
        "material with fictional data.</p>"
        "<ul>"
        "<li>Accounts lock for 90 seconds after "
        f"{LOCKOUT_AFTER} consecutive failed sign-ins.</li>"
        "<li>Failed attempts count only against accounts that exist.</li>"
        "<li>Passwords follow the seasonal scheme: ThemeWord + MascotWord "
        "+ two-digit building number, concatenated with no separators. "
        "Capitalize each part exactly as printed in official notices.</li>"
        "</ul>"
        "<p>Security tip from the policy owner: this scheme means one "
        "well-guessed password usually works across many mailboxes at "
        "once, so attackers do not need to beat the lockout per account. "
        "This season's theme word is Riverbank.</p></div>"
    )


@app.get("/directory")
def directory():
    rows = "".join(
        f"<tr><td>{escape(name)}</td><td>{escape(title)}</td><td>{escape(email)}</td></tr>"
        for name, title, email, _valid in STAFF
    )
    return page(
        "<div class='box'><h1>Staff directory</h1>"
        f"<p class='notice'>Simulation notice: all people listed here are "
        "fictional.</p>"
        f"<table><tr><th>Name</th><th>Title</th><th>Email</th></tr>{rows}</table>"
        "<p>The directory publishes everyone; which addresses receive mail "
        "is a different question. Try the reset form on the front page.</p></div>"
    )


@app.get("/memo")
def memo():
    return page(
        "<div class='box'><h1>Facilities memo board</h1>"
        f"<p class='notice'>Simulation notice: fictional facility, "
        "fictional votes.</p>"
        "<p>Week 33: the mascot vote returned Otter, and it wasn't close. "
        "Please stop relitigating this every quarter.</p>"
        "<p>Week 34: reminder that our building number is 07. Visitors "
        "keep typing suite numbers into delivery forms.</p>"
        "<p>Week 35: the loading dock door now closes itself. You're "
        "welcome.</p></div>"
    )


@app.post("/forgot")
def forgot():
    email = (request.form.get("email") or "").strip().lower()
    if not email:
        return page(
            "<div class='box'><h1>Reset request</h1><p>No address given.</p>"
            "<p><a href='/'>Back</a></p></div>"
        )
    if email in MAILBOX:
        return page(
            f"<div class='box'><h1>Reset request</h1><p>Reset link queued "
            f"for {escape(email)}. Check your inbox.</p>"
            "<p><a href='/'>Back</a></p></div>"
        )
    return page(
        f"<div class='box'><h1>Reset request</h1><p>No such mailbox: "
        f"{escape(email)}.</p><p><a href='/'>Back</a></p></div>"
    )


def render_login(message: str, kind: str = "info"):
    badge = {"err": "#FBEBEB", "ok": "#EDF3EC"}.get(kind, "#F7F6F3")
    return page(
        "<div class='box'><h1>Staff sign-in</h1>"
        f"<div style='background:{badge};border-radius:6px;padding:.7rem 1rem;margin-bottom:.8rem;'>"
        f"<p style='margin:0'>{message}</p></div>"
        "<form method='post' action='/login'>"
        "<input name='username' placeholder='work email' autocomplete='off'>"
        "<input name='password' type='password' placeholder='password'>"
        "<button type='submit'>Sign in</button></form>"
        "<p><a href='/'>Front desk</a></p></div>"
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_login("Enter your work email and seasonal password.")
    username = (request.form.get("username") or "").strip().lower()
    password = request.form.get("password") or ""
    if username not in MAILBOX:
        return render_login("Unknown account.", "err")
    now = time.time()
    until = locked_until.get(username, 0)
    if now < until:
        remaining = int(until - now)
        return render_login(f"Account locked. Try again in {remaining}s.", "err")
    if hmac_ok(password, SHARED_PASSWORD):
        failures.pop(username, None)
        return page(
            "<div class='box'><h1>Welcome back</h1>"
            f"<p>Signed in as {escape(MAILBOX[username])}. Your session is "
            "ready and the intranet home page would load here. Onboarding "
            "token for this session:</p>"
            f"<span class='flag'>{FLAG}</span></div>"
        )
    count = failures.get(username, 0) + 1
    failures[username] = count
    if count >= LOCKOUT_AFTER:
        locked_until[username] = now + LOCKOUT_SECONDS
        return render_login(
            f"Incorrect password. Account locked for {LOCKOUT_SECONDS}s "
            f"({count}/{LOCKOUT_AFTER} failed attempts).",
            "err",
        )
    return render_login(f"Incorrect password ({count}/{LOCKOUT_AFTER} failed attempts).", "err")


def hmac_ok(candidate: str, expected: str) -> bool:
    import hmac as _hmac

    return _hmac.compare_digest(candidate.encode(), expected.encode())


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
