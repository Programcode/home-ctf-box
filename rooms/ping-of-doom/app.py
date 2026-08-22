from flask import Flask, request
from markupsafe import escape
import subprocess

app = Flask(__name__)

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>NetCheck 3000</title>
<style>
body { background:#F7F6F3; font-family:'Helvetica Neue',Helvetica,Arial,sans-serif; display:flex; justify-content:center; padding-top:10vh; }
.box { background:#fff; border:1px solid #EAEAEA; border-radius:8px; padding:2.5rem; width:30rem; }
h1 { font-family:Georgia,serif; letter-spacing:-0.02em; font-size:1.4rem; margin-bottom:.5rem; }
p { color:#787774; font-size:.88rem; margin-bottom:1rem; }
input { width:100%%; padding:.5rem .75rem; border:1px solid #EAEAEA; border-radius:6px; font-family:ui-monospace,Menlo,monospace; font-size:.9rem; }
button { background:#111; color:#fff; border:none; border-radius:6px; padding:.5rem 1.2rem; margin-top:.6rem; cursor:pointer; }
button:hover { background:#333; }
pre { background:#F7F6F3; border:1px solid #EAEAEA; border-radius:6px; padding:1rem; margin-top:1.2rem; overflow:auto; font-size:.8rem; line-height:1.45; }
</style></head><body>%s</body></html>"""

FORM = """<div class="box">
<h1>NetCheck 3000</h1>
<p>Enterprise-grade host diagnostics. Enter a hostname or IP to ping it.</p>
<form method="post" action="/ping">
<input name="host" placeholder="e.g. 127.0.0.1" autocomplete="off">
<br><button type="submit">Ping</button>
</form>
%s
</div>"""


@app.route("/")
def index():
    return PAGE % (FORM % "")


@app.route("/ping", methods=["POST"])
def ping():
    host = (request.form.get("host") or "").strip()
    if not host:
        return PAGE % (FORM % "<pre>enter a host first</pre>")
    cmd = f"ping -c 2 -W 1 {host}"
    try:
        proc = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=15
        )
        out = (proc.stdout + proc.stderr).strip()
    except subprocess.TimeoutExpired:
        out = "command timed out"
    return PAGE % (FORM % f"<pre>{escape(out)}</pre>")


app.run(host="0.0.0.0", port=5000)
