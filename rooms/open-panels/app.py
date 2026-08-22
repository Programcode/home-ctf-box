import os

from flask import Flask, jsonify

app = Flask(__name__)
FLAG = os.environ["FLAG_7"]

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>DocuHub</title>
<style>
body { background:#F7F6F3; font-family:'Helvetica Neue',Helvetica,Arial,sans-serif; display:flex; justify-content:center; padding-top:12vh; }
.box { background:#fff; border:1px solid #EAEAEA; border-radius:8px; padding:2.5rem; width:28rem; }
h1 { font-family:Georgia,serif; letter-spacing:-0.02em; font-size:1.4rem; margin-bottom:.5rem; }
li { margin:.4rem 0; color:#787774; font-size:.88rem; }
p { color:#787774; font-size:.88rem; }
code { font-family:ui-monospace,Menlo,monospace; font-size:.85rem; background:#F7F6F3; border:1px solid #EAEAEA; border-radius:4px; padding:.1rem .4rem; }
</style></head><body>__BODY__</body></html>"""


@app.route("/")
def index():
    body = (
        '<div class="box"><h1>DocuHub</h1>'
        "<p>The tiny documentation site for the Acme platform.</p>"
        "<ul>"
        "<li>Getting started in under five minutes</li>"
        "<li>REST API reference with copy-paste examples</li>"
        "<li>Self-hosting guide and FAQ</li>"
        "</ul>"
        "<p>Maintained by the platform team. Status page at "
        "<code>/status</code>, diagnostics at <code>/debug</code>.</p></div>"
    )
    return PAGE.replace("__BODY__", body)


@app.route("/debug")
def debug():
    return jsonify(
        {
            "service": "DocuHub",
            "version": "0.3.1-beta",
            "uptime_seconds": 42133,
            "env": {"FLAG_7": FLAG},
            "config": {
                "db_host": "internal-db.acme.local",
                "db_port": 5432,
                "cache_backend": "memory",
                "feature_flags": {"new_editor": True, "billing_v2": False},
            },
        }
    )


app.run(host="0.0.0.0", port=5000)
