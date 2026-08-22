from flask import Flask, request
from markupsafe import escape
import os
import re

app = Flask(__name__)
FLAG = os.environ["FLAG_9"]
VAULT_CODE = "Xk9-Vq2-Lm4-Tz7"

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Vault Keypad</title>
<style>
body { background:#F7F6F3; font-family:'Helvetica Neue',Helvetica,Arial,sans-serif; display:flex; justify-content:center; padding-top:12vh; }
.box { background:#fff; border:1px solid #EAEAEA; border-radius:8px; padding:2.5rem; width:24rem; }
h1 { font-family:Georgia,serif; letter-spacing:-0.02em; font-size:1.4rem; margin-bottom:1rem; }
input { width:100%; padding:.5rem .75rem; margin:.3rem 0; border:1px solid #EAEAEA; border-radius:6px; }
button { background:#111; color:#fff; border:none; border-radius:6px; padding:.5rem 1rem; margin-top:.6rem; cursor:pointer; }
button:hover { background:#333; }
p { color:#787774; font-size:.88rem; }
code { font-family:ui-monospace,Menlo,monospace; font-size:.85rem; background:#F7F6F3; border:1px solid #EAEAEA; border-radius:4px; padding:.1rem .4rem; }
pre { background:#F7F6F3; border:1px solid #EAEAEA; border-radius:6px; padding:1rem; overflow:auto; font-size:.8rem; }
.flag { background:#EDF3EC; color:#346538; border-radius:9999px; padding:.3rem 1rem; font-family:ui-monospace,Menlo,monospace; font-size:.85rem; display:inline-block; }
</style></head><body>{BODY}</body></html>"""


def page(body):
    return PAGE.replace("{BODY}", body)


@app.route("/")
def index():
    return page(
        '<div class="box"><h1>Vault Keypad</h1>'
        "<p>The vault opens when your code matches ours. Comparison is done with "
        "<code>re.fullmatch(your_input, vault_code)</code>. Enter the pattern below.</p>"
        '<form method="post" action="/unlock">'
        '<input name="code" placeholder="access code" autocomplete="off">'
        "<button type='submit'>Unlock</button></form></div>"
    )


@app.route("/unlock", methods=["POST"])
def unlock():
    code = request.form.get("code", "")
    try:
        matched = re.fullmatch(code, VAULT_CODE)
    except re.error as exc:
        return page(
            f'<div class="box"><h1>Keypad error</h1><pre>{escape(str(exc))}</pre></div>'
        )
    if matched:
        return page(
            '<div class="box"><h1>Unlocked</h1><p>Vault contents:</p>'
            f"<span class='flag'>{FLAG}</span></div>"
        )
    return page(
        '<div class="box"><h1>Denied</h1><p>That code does not match.</p></div>'
    )


app.run(host="0.0.0.0", port=5000)
