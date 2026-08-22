from flask import Flask, Response, request
from urllib.parse import parse_qs
import os

app = Flask(__name__)
FLAG = os.environ["FLAG_17"]

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Cartly</title>
<style>
body { background:#F7F6F3; font-family:'Helvetica Neue',Helvetica,Arial,sans-serif; display:flex; justify-content:center; padding-top:12vh; }
.box { background:#fff; border:1px solid #EAEAEA; border-radius:8px; padding:2.5rem; width:26rem; }
h1 { font-family:Georgia,serif; letter-spacing:-0.02em; font-size:1.4rem; margin-bottom:1rem; }
p { color:#787774; font-size:.88rem; }
code { font-family:ui-monospace,Menlo,monospace; font-size:.85rem; background:#F7F6F3; border:1px solid #EAEAEA; border-radius:4px; padding:.1rem .4rem; }
</style></head><body>__BODY__</body></html>"""


def page(body):
    return PAGE.replace("__BODY__", body)


USAGE = (
    '<div class="box"><h1>Cartly checkout</h1>'
    "<p>Apply a coupon at checkout:</p>"
    "<p><code>GET /checkout?price=&lt;cents&gt;&amp;discount=&lt;pct&gt;</code></p>"
    "<p>Coupons above 50 percent are rejected.</p></div>"
)


@app.route("/")
def index():
    return page(USAGE)


@app.route("/checkout")
def checkout():
    d = parse_qs(request.query_string.decode())
    if "price" not in d or "discount" not in d:
        return page(USAGE)
    try:
        price = int(d["price"][0])
    except ValueError:
        return Response("invalid price\n", status=400)
    if not 1 <= price <= 100000:
        return Response("price out of range\n", status=400)
    try:
        checked = int(d["discount"][0])
    except ValueError:
        return Response("invalid coupon\n", status=400)
    if checked > 50:
        return Response("coupon too generous\n", status=400)
    try:
        total = price - int(d["discount"][-1])
    except ValueError:
        return Response("invalid coupon\n", status=400)
    if total < 0:
        body = (
            '<div class="box"><h1>Order complete</h1>'
            f"<p>Coupon over-applied by {-total}. A refund has been issued to your account.</p>"
            f"<p>Refund reference: <code>{FLAG}</code></p></div>"
        )
        return page(body)
    body = (
        f'<div class="box"><h1>Order complete</h1>'
        f"<p>Total due: <code>{total}</code></p></div>"
    )
    return page(body)


app.run(host="0.0.0.0", port=5000)
