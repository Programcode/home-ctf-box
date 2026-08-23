"""Ledgerly invoicing: deliberately missing ownership checks. Room target only."""

import os

from flask import Flask
from markupsafe import escape

app = Flask(__name__)
FLAG = os.environ["ROOM_FLAG"]

INVOICES = {
    1041: {
        "owner": "Alice Kelemen",
        "vendor": "Bean Scene Catering",
        "issued": "2026-06-02",
        "amount": "EUR 84.00",
        "status": "paid",
        "lines": ["Office coffee service, June", "Delivery surcharge"],
    },
    1042: {
        "owner": "Alice Kelemen",
        "vendor": "Danube Paper Supply",
        "issued": "2026-06-11",
        "amount": "EUR 31.50",
        "status": "open",
        "lines": ["A4 reams x20", "Sticky notes"],
    },
    1043: {
        "owner": "Alice Kelemen",
        "vendor": "BudaPrint Services",
        "issued": "2026-06-18",
        "amount": "EUR 120.00",
        "status": "disputed",
        "lines": ["Conference banner", "Rush fee"],
    },
    1044: {
        "owner": "Bob Farago",
        "vendor": "Bean Scene Catering",
        "issued": "2026-06-19",
        "amount": "EUR 512.00",
        "status": "pending",
        "lines": ["Offsite catering deposit", f"Internal release code: {FLAG}"],
    },
}

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Ledgerly</title>
<style>
body { background:#F7F6F3; font-family:Helvetica,Arial,sans-serif; display:flex; justify-content:center; padding-top:10vh; }
.box { background:#fff; border:1px solid #EAEAEA; border-radius:8px; padding:2.5rem; width:34rem; }
h1 { font-family:Georgia,serif; letter-spacing:-0.02em; font-size:1.4rem; margin-bottom:.5rem; }
p { color:#787774; font-size:.88rem; }
table { border-collapse:collapse; width:100%%; margin-top:1rem; }
td, th { text-align:left; padding:.45rem .6rem; border-bottom:1px solid #EAEAEA; font-size:.86rem; }
th { color:#787774; font-weight:normal; }
a { color:#111; }
.badge { display:inline-block; border-radius:9999px; padding:.15rem .7rem; font-size:.75rem; background:#F1EFEA; color:#57554E; }
dl { margin-top:1rem; font-size:.9rem; }
dt { color:#787774; margin-top:.7rem; }
dd { margin:.2rem 0 0; }
ul { color:#444; font-size:.88rem; }
</style></head><body>%s</body></html>"""


def _invoice_html(inv_id: int, inv: dict) -> str:
    rows = "".join(f"<li>{escape(line)}</li>" for line in inv["lines"])
    return f"""
<div class="box">
<h1>Invoice #{inv_id}</h1>
<dl>
<dt>Billed to</dt><dd>{escape(inv["owner"])}</dd>
<dt>Vendor</dt><dd>{escape(inv["vendor"])}</dd>
<dt>Issued</dt><dd>{inv["issued"]}</dd>
<dt>Amount</dt><dd>{inv["amount"]} <span class="badge">{inv["status"]}</span></dd>
<dt>Line items</dt><dd><ul>{rows}</ul></dd>
</dl>
<p><a href="/">&larr; back to dashboard</a></p>
</div>"""


@app.get("/healthz")
def healthz():
    return "ok"


@app.get("/")
def home():
    rows = "".join(
        f"<tr><td><a href='/invoice/{iid}'>#{iid}</a></td>"
        f"<td>{escape(inv['vendor'])}</td><td>{inv['amount']}</td></tr>"
        for iid, inv in INVOICES.items()
        if inv["owner"] == "Alice Kelemen"
    )
    return (
        PAGE
        % f"""
<div class="box">
<h1>Ledgerly</h1>
<p>Signed in as <strong>alice@ledgerly.test</strong>. Your open invoices:</p>
<table><tr><th>Invoice</th><th>Vendor</th><th>Amount</th></tr>{rows}</table>
</div>"""
    )


@app.get("/invoice/<int:invoice_id>")
def invoice(invoice_id: int):
    # Loads whatever record the URL names. Nobody here checks that the
    # signed-in user actually owns the invoice.
    inv = INVOICES.get(invoice_id)
    if inv is None:
        return PAGE % (
            "<div class='box'><h1>Not found</h1><p>No such invoice.</p>"
            "<p><a href='/'>&larr; back to dashboard</a></p></div>"
        )
    return PAGE % _invoice_html(invoice_id, inv)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
