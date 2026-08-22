from flask import Flask, Response, request
from markupsafe import escape
import io
import os
import xml.sax
import xml.sax.handler

app = Flask(__name__)


class Collector(xml.sax.handler.ContentHandler):
    def __init__(self):
        self.parts = []

    def characters(self, content):
        self.parts.append(content)


PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>ImportBridge</title>
<style>
body { background:#F7F6F3; font-family:'Helvetica Neue',Helvetica,Arial,sans-serif; display:flex; justify-content:center; padding-top:10vh; }
.box { background:#fff; border:1px solid #EAEAEA; border-radius:8px; padding:2.5rem; width:30rem; }
h1 { font-family:Georgia,serif; letter-spacing:-0.02em; font-size:1.4rem; margin-bottom:1rem; }
p { color:#787774; font-size:.88rem; }
code { font-family:ui-monospace,Menlo,monospace; font-size:.85rem; background:#F7F6F3; border:1px solid #EAEAEA; border-radius:4px; padding:.1rem .4rem; }
pre { background:#F7F6F3; border:1px solid #EAEAEA; border-radius:6px; padding:1rem; overflow:auto; font-size:.8rem; }
</style></head><body>{BODY}</body></html>"""


@app.route("/")
def index():
    return PAGE.replace(
        "{BODY}",
        '<div class="box"><h1>ImportBridge</h1>'
        "<p>Bulk XML importer for legacy partners.</p>"
        "<p><code>POST /import</code> with an XML document body. Entities are fully supported.</p></div>",
    )


@app.route("/import", methods=["POST"])
def do_import():
    body = request.get_data(as_text=True)
    handler = Collector()
    try:
        parser = xml.sax.make_parser()
        parser.setFeature(xml.sax.handler.feature_external_ges, True)
        parser.setContentHandler(handler)
        parser.parse(io.StringIO(body))
    except Exception as exc:
        return Response(f"parse error: {exc}\n", status=400, mimetype="text/plain")
    text = escape("".join(handler.parts).strip())
    return PAGE.replace(
        "{BODY}",
        f'<div class="box"><h1>Import result</h1><p>Imported content:</p><pre>{text}</pre></div>',
    )


app.run(host="0.0.0.0", port=5000)
