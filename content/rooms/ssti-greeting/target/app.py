"""Greeting Card Studio: deliberately vulnerable to Jinja SSTI. Room target only."""

from flask import Flask, render_template_string, request

app = Flask(__name__)

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Greeting Card Studio</title>
<style>
body { background:#F7F6F3; font-family:Helvetica,Arial,sans-serif; display:flex; justify-content:center; padding-top:10vh; }
.box { background:#fff; border:1px solid #EAEAEA; border-radius:8px; padding:2.5rem; width:30rem; }
h1 { font-family:Georgia,serif; letter-spacing:-0.02em; font-size:1.4rem; margin-bottom:.5rem; }
p { color:#787774; font-size:.88rem; margin-bottom:1rem; }
input { width:100%%; padding:.5rem .75rem; border:1px solid #EAEAEA; border-radius:6px; }
button { background:#111; color:#fff; border:none; border-radius:6px; padding:.5rem 1.2rem; margin-top:.6rem; cursor:pointer; }
.card { background:#FBF7EF; border:1px dashed #D8CDB8; border-radius:6px; padding:1rem; margin-top:1.2rem; font-size:1rem; color:#5A4632; }
</style></head><body>%s</body></html>"""

FORM = """<div class="box">
<h1>Greeting Card Studio</h1>
<p>Compose a personalized card. Enter the recipient's name and we render the greeting for you.</p>
<form method="post" action="/greet">
<input name="name" placeholder="recipient name" autocomplete="off">
<br><button type="submit">Preview card</button>
</form>
%s
</div>"""


@app.get("/healthz")
def healthz():
    return "ok"


@app.get("/")
def home():
    return PAGE % (FORM % "")


@app.post("/greet")
def greet():
    name = (request.form.get("name") or "").strip()
    if not name:
        return PAGE % (FORM % "<p class='note'>enter a recipient first</p>")
    # The greeting is assembled by string formatting, so the name becomes
    # part of the template source itself.
    template = f"<h2>Hello {name}, enjoy your card.</h2>"
    rendered = render_template_string(template)
    return PAGE % (FORM % f"<div class='card'>{rendered}</div>")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
