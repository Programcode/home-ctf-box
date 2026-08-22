from flask import Flask, request
import os

app = Flask(__name__)
FLAG = os.environ["FLAG_20"]
CTX = {"user": "guest", "plan": "free", "flag": FLAG}

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Portal</title>
<style>
body { background:#F7F6F3; font-family:'Helvetica Neue',Helvetica,Arial,sans-serif; display:flex; justify-content:center; padding-top:12vh; }
.box { background:#fff; border:1px solid #EAEAEA; border-radius:8px; padding:2.5rem; width:26rem; }
h1 { font-family:Georgia,serif; letter-spacing:-0.02em; font-size:1.4rem; margin-bottom:1rem; }
p { color:#787774; font-size:.88rem; }
code { font-family:ui-monospace,Menlo,monospace; font-size:.85rem; background:#F7F6F3; border:1px solid #EAEAEA; border-radius:4px; padding:.1rem .4rem; }
</style></head><body>__BODY__</body></html>"""


def page(body):
    return PAGE.replace("__BODY__", body)


@app.route("/")
@app.route("/welcome")
def welcome():
    name = request.args.get("name", "")
    fmt = "<h2>Welcome " + name + "</h2><p>Your plan: {plan}</p>"
    try:
        out = fmt.format(**CTX)
    except (KeyError, IndexError):
        return page('<div class="box"><h1>Oops</h1><p>bad name</p></div>')
    return page(out)


app.run(host="0.0.0.0", port=5000)
