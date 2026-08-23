"""PanelOps status board: ships an undocumented debug panel. Room target only."""

import os
import platform

from flask import Flask

app = Flask(__name__)

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>PanelOps</title>
<style>
body { background:#F7F6F3; font-family:Helvetica,Arial,sans-serif; display:flex; justify-content:center; padding-top:10vh; }
.box { background:#fff; border:1px solid #EAEAEA; border-radius:8px; padding:2.5rem; width:34rem; }
h1 { font-family:Georgia,serif; letter-spacing:-0.02em; font-size:1.4rem; margin-bottom:.5rem; }
p { color:#787774; font-size:.88rem; }
table { border-collapse:collapse; width:100%%; margin-top:1rem; }
td, th { text-align:left; padding:.45rem .6rem; border-bottom:1px solid #EAEAEA; font-size:.86rem; }
th { color:#787774; font-weight:normal; }
.ok { color:#346538; } .degraded { color:#A05A2C; }
pre { background:#F7F6F3; border:1px solid #EAEAEA; border-radius:6px; padding:1rem; overflow:auto; font-size:.8rem; line-height:1.5; margin-top:1rem; }
h2 { font-size:1rem; margin-top:1.4rem; }
</style></head><body>%s</body></html>"""


@app.get("/healthz")
def healthz():
    return "ok"


@app.get("/")
def home():
    return (
        PAGE
        % """
<div class="box">
<h1>PanelOps</h1>
<p>Internal status board for the lab services.</p>
<table>
<tr><th>Service</th><th>Status</th></tr>
<tr><td>billing-api</td><td class="ok">operational</td></tr>
<tr><td>search-indexer</td><td class="ok">operational</td></tr>
<tr><td>report-builder</td><td class="degraded">degraded</td></tr>
</table>
<!-- TODO: retire the old /debug panel before we ship this to customers -->
</div>"""
    )


@app.get("/robots.txt")
def robots():
    return "User-agent: *\nDisallow: /debug\n"


@app.get("/debug")
def debug():
    # Leftover diagnostics page. Prints the process environment to
    # anyone who asks, room flag included.
    flag = os.environ.get("ROOM_FLAG", "unset")
    report = (
        f"build: panelops 0.9.4 (staging)\n"
        f"python: {platform.python_version()}\n"
        "workers: 1\n\n"
        "environment:\n"
        f"  ROOM_FLAG={flag}\n"
        "  FLASK_ENV=production\n"
    )
    return PAGE % (
        """
<div class="box">
<h1>Debug panel</h1>
<p>Runtime diagnostics for on-call engineers. Do not share externally.</p>
<pre>%s</pre>
</div>"""
        % report
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
