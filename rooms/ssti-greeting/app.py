from flask import Flask, render_template_string, request
import os

app = Flask(__name__)
FLAG = os.environ["FLAG_4"]
app.jinja_env.globals["secret_flag"] = FLAG

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Greetify</title>
<style>
body { background:#F7F6F3; font-family:'Helvetica Neue',Helvetica,Arial,sans-serif; display:flex; justify-content:center; padding-top:12vh; }
.box { background:#fff; border:1px solid #EAEAEA; border-radius:8px; padding:2.5rem; width:26rem; }
h1 { font-family:Georgia,serif; letter-spacing:-0.02em; font-size:1.4rem; margin-bottom:.5rem; }
p { color:#787774; font-size:.88rem; }
input { width:100%; padding:.5rem .75rem; border:1px solid #EAEAEA; border-radius:6px; font-size:.9rem; }
button { background:#111; color:#fff; border:none; border-radius:6px; padding:.5rem 1.2rem; margin-top:.6rem; cursor:pointer; }
button:hover { background:#333; }
h2 { margin-top:1.2rem; }
</style></head><body>__BODY__</body></html>"""

FORM = """<div class="box">
<h1>Greetify</h1>
<p>Craft a personalized greeting card for someone you care about.</p>
<form method="post" action="/greet">
<input name="name" placeholder="Who is the card for?" autocomplete="off">
<br><button type="submit">Send card</button>
</form>
</div>"""


@app.route("/")
def index():
    return PAGE.replace("__BODY__", FORM)


@app.route("/greet", methods=["POST"])
def greet():
    name = request.form.get("name", "")
    html = "<h2>Hello " + name + "</h2>"
    return PAGE.replace("__BODY__", render_template_string(html))


app.run(host="0.0.0.0", port=5000)
