"""Signal Vault lock: user input compiled as the regex pattern. Room target only."""

import os
import re

from flask import Flask, request
from markupsafe import escape

app = Flask(__name__)
FLAG = os.environ["ROOM_FLAG"]
SECRET_CODE = "Qw7-Bn2-Fr8-Kd5"

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Signal Vault</title>
<style>
body { background:#F7F6F3; font-family:Helvetica,Arial,sans-serif; display:flex; justify-content:center; padding-top:12vh; }
.box { background:#fff; border:1px solid #EAEAEA; border-radius:8px; padding:2.5rem; width:24rem; }
h1 { letter-spacing:-0.02em; font-size:1.4rem; margin-bottom:1rem; }
input { width:100%%; padding:.5rem .75rem; margin:.3rem 0; border:1px solid #EAEAEA; border-radius:6px; }
button { background:#111; color:#fff; border:none; border-radius:6px; padding:.5rem 1rem; margin-top:.6rem; cursor:pointer; }
button:hover { background:#333; }
p { color:#787774; font-size:.88rem; }
code { font-family:ui-monospace,Menlo,monospace; font-size:.85rem; background:#F7F6F3; border:1px solid #EAEAEA; border-radius:4px; padding:.1rem .4rem; }
pre { background:#F7F6F3; border:1px solid #EAEAEA; border-radius:6px; padding:1rem; overflow:auto; font-size:.8rem; }
.flag { background:#EDF3EC; color:#346538; border-radius:9999px; padding:.3rem 1rem; font-family:ui-monospace,Menlo,monospace; font-size:.85rem; display:inline-block; }
</style></head><body>{BODY}</body></html>"""


def page(body: str) -> str:
    return PAGE.replace("{BODY}", body)


@app.get("/healthz")
def healthz() -> str:
    return "ok"


@app.get("/")
def index() -> str:
    return page(
        '<div class="box"><h1>Signal Vault</h1>'
        "<p>The lock opens when your pattern matches our access code. The check runs "
        "<code>re.fullmatch(your_input, access_code)</code>, so type a pattern, not the code.</p>"
        '<form method="post" action="/unlock">'
        '<input name="code" placeholder="pattern" autocomplete="off">'
        "<button type='submit'>Unlock</button></form></div>"
    )


@app.post("/unlock")
def unlock() -> str:
    pattern = request.form.get("code", "")
    try:
        hit = re.fullmatch(pattern, SECRET_CODE)
    except re.error as exc:
        return page(f'<div class="box"><h1>Lock error</h1><pre>{escape(str(exc))}</pre></div>')
    if hit:
        return page(
            '<div class="box"><h1>Unlocked</h1><p>Vault contents:</p>'
            f"<span class='flag'>{FLAG}</span></div>"
        )
    return page(
        '<div class="box"><h1>Denied</h1><p>That pattern does not match the access code.</p></div>'
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
