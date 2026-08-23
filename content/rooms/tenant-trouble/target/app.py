"""Ledgerline invoicing: workspace identity comes straight from a header. Room target only."""

import os

from flask import Flask, request

app = Flask(__name__)
FLAG = os.environ["ROOM_FLAG"]

TENANTS = {
    "acme": "Acme Corp",
    "globex": "Globex Ltd",
    "initech": "Initech LLC",
}

# One platform-wide ledger. Invoice numbers are continuous across tenants,
# and the authorization check compares against whatever the client claims.
LEDGER = {
    "INV-1001": {
        "tenant": "acme",
        "vendor": "Cloudline Hosting",
        "issued": "2026-06-02",
        "amount_eur": 412.50,
        "memo": "June hosting renewal.",
    },
    "INV-1002": {
        "tenant": "acme",
        "vendor": "Budapest Print Co",
        "issued": "2026-06-11",
        "amount_eur": 88.20,
        "memo": "Onboarding packs for new hires.",
    },
    "INV-1003": {
        "tenant": "acme",
        "vendor": "Metrolink Transit",
        "issued": "2026-07-01",
        "amount_eur": 45.00,
        "memo": "Monthly transit passes.",
    },
    "INV-1030": {
        "tenant": "initech",
        "vendor": "ServerRoom Kft",
        "issued": "2026-06-19",
        "amount_eur": 1200.00,
        "memo": "Rack deposit, colo cage 4.",
    },
    "INV-1042": {
        "tenant": "globex",
        "vendor": "Ledgerworks Audit",
        "issued": "2026-07-15",
        "amount_eur": 9600.00,
        "memo": f"Q3 reconciliation note: {FLAG}",
    },
}

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Ledgerline</title>
<style>
body { background:#F7F6F3; font-family:Helvetica,Arial,sans-serif; display:flex; justify-content:center; padding-top:10vh; }
.box { background:#fff; border:1px solid #EAEAEA; border-radius:8px; padding:2.5rem; width:32rem; }
h1 { letter-spacing:-0.02em; font-size:1.4rem; margin-bottom:1rem; }
p, li, td { color:#787774; font-size:.9rem; }
table { border-collapse:collapse; width:100%%; margin-top:.5rem; }
td, th { text-align:left; padding:.35rem .5rem; border-bottom:1px solid #EAEAEA; }
code { background:#F7F6F3; border:1px solid #EAEAEA; border-radius:6px; padding:.15rem .4rem; font-size:.82rem; }
.flag { background:#EDF3EC; color:#346538; border-radius:9999px; padding:.35rem 1rem; display:inline-block; }
a { color:#346538; }
</style></head><body>%s</body></html>"""


def current_tenant() -> str:
    return request.headers.get("Tenant-ID", "acme")


@app.get("/healthz")
def healthz():
    return "ok"


@app.get("/")
def dashboard():
    slug = current_tenant()
    label = TENANTS.get(slug)
    if label is None:
        return (
            PAGE
            % f"""
<div class="box"><h1>Ledgerline</h1>
<p>No workspace is provisioned under the identifier
<code>{slug}</code>. Ask your account manager about onboarding.</p></div>"""
        )
    count = sum(1 for inv in LEDGER.values() if inv["tenant"] == slug)
    return (
        PAGE
        % f"""
<div class="box">
<h1>Ledgerline dashboard</h1>
<p>Signed in to <strong>{label}</strong> ({count} invoices on file).</p>
<p>Demo mode resolves workspaces from the <code>Tenant-ID</code>
header. Requests that omit it land in the Acme Corp sandbox.</p>
<ul><li><a href="/invoices">Open your invoice ledger</a></li>
<li><a href="/customers">Customers on the platform</a></li></ul>
</div>"""
    )


@app.get("/customers")
def customers():
    rows = "".join(
        f"<tr><td>{label}</td><td><code>{slug}</code></td></tr>"
        for slug, label in sorted(TENANTS.items())
    )
    return (
        PAGE
        % f"""
<div class="box">
<h1>Customers on Ledgerline</h1>
<table><tr><th>Company</th><th>Workspace slug</th></tr>{rows}</table>
<p>Every invoice line references one of these workspaces.</p>
</div>"""
    )


@app.get("/invoices")
def invoices():
    slug = current_tenant()
    mine = sorted(k for k, v in LEDGER.items() if v["tenant"] == slug)
    if not mine:
        return (
            PAGE
            % f"""
<div class="box"><h1>Invoices</h1><p>Nothing filed for workspace
<code>{slug}</code>.</p></div>"""
        )
    rows = "".join(
        f'<li><a href="/invoices/{inv}">{inv}</a>, {LEDGER[inv]["vendor"]}, '
        f"{LEDGER[inv]['amount_eur']:.2f} EUR</li>"
        for inv in mine
    )
    return (
        PAGE
        % f"""
<div class="box">
<h1>Invoices for {TENANTS.get(slug, slug)}</h1>
<ul>{rows}</ul>
<p>Invoice numbers come from one platform-wide ledger. Gaps in your
list belong to neighboring workspaces.</p>
</div>"""
    )


@app.get("/invoices/<invoice_id>")
def invoice_detail(invoice_id: str):
    slug = current_tenant()
    inv = LEDGER.get(invoice_id.upper())
    if inv is None:
        return (
            PAGE
            % """
<div class="box"><h1>Not found</h1><p>The platform ledger currently
spans INV-1001 through INV-1050.</p></div>""",
            404,
        )
    if inv["tenant"] != slug:
        # Identity equals whatever the caller sends, so this check only
        # stops honest requests.
        return (
            PAGE
            % f"""
<div class="box"><h1>Cross-tenant access denied</h1><p>Invoice
<code>{invoice_id.upper()}</code> does not belong to workspace
<code>{slug}</code>.</p></div>""",
            403,
        )
    return (
        PAGE
        % f"""
<div class="box">
<h1>Invoice {invoice_id.upper()}</h1>
<table>
<tr><th>Vendor</th><td>{inv["vendor"]}</td></tr>
<tr><th>Issued</th><td>{inv["issued"]}</td></tr>
<tr><th>Amount</th><td>{inv["amount_eur"]:.2f} EUR</td></tr>
<tr><th>Memo</th><td>{inv["memo"]}</td></tr>
</table>
</div>"""
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
