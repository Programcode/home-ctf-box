"""Meridian Pay sandbox: the withdrawal path reads, sleeps, then writes. Room target only."""

import os
import secrets
import threading
import time
from dataclasses import dataclass

from flask import Flask, jsonify, request

app = Flask(__name__)
FLAG = os.environ["ROOM_FLAG"]

STARTING_BALANCE_CENTS = 10_000
FRAUD_CHECK_SECONDS = 0.08


@dataclass(slots=True)
class Account:
    name: str
    opening_balance_cents: int = STARTING_BALANCE_CENTS
    withdrawn_cents: int = 0


def balance_of(account: Account) -> int:
    return account.opening_balance_cents - account.withdrawn_cents


accounts: dict[str, Account] = {}
_accounts_lock = threading.Lock()

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Meridian Pay</title>
<style>
body { background:#F7F6F3; font-family:Helvetica,Arial,sans-serif; display:flex; justify-content:center; padding-top:10vh; }
.box { background:#fff; border:1px solid #EAEAEA; border-radius:8px; padding:2.5rem; width:32rem; }
h1 { letter-spacing:-0.02em; font-size:1.4rem; margin-bottom:1rem; }
p, li { color:#787774; font-size:.9rem; }
code, pre { background:#F7F6F3; border:1px solid #EAEAEA; border-radius:6px; padding:.15rem .4rem; font-size:.82rem; }
pre { padding:1rem; overflow:auto; }
.flag { background:#EDF3EC; color:#346538; border-radius:9999px; padding:.35rem 1rem; display:inline-block; }
input { width:100%%; padding:.5rem .75rem; margin:.3rem 0; border:1px solid #EAEAEA; border-radius:6px; }
button { background:#111; color:#fff; border:none; border-radius:6px; padding:.55rem 1rem; margin-top:.6rem; width:100%%; cursor:pointer; }
a { color:#346538; }
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
<h1>Meridian Pay sandbox</h1>
<p>Payment rails for testing transfer logic. Open a sandbox account to
try the withdrawals API; every account starts at 100.00 EUR.</p>
<form method="post" action="/open">
<input name="name" placeholder="account holder name" autocomplete="off">
<button type="submit">Open sandbox account</button>
</form>
<p>Transfers process in parallel on our workers. The fraud scorer holds
a balance snapshot for a moment before funds move.</p>
</div>"""
    )


@app.post("/open")
def open_account():
    name = request.form.get("name", "").strip()
    if not name:
        return (
            PAGE
            % "<div class='box'><h1>Name required</h1><p>Go back and name the account holder.</p></div>",
            400,
        )
    token = secrets.token_hex(8)
    with _accounts_lock:
        accounts[token] = Account(name=name)
    return (
        PAGE
        % f"""
<div class="box">
<h1>Account opened for {name}</h1>
<p>Account token: <code class="acct">{token}</code></p>
<p>Balance: 100.00 EUR.</p>
<p>Withdraw with a form or curl:</p>
<pre>curl -X POST http://this-host/withdraw \\
  -d token={token} -d amount_cents=6000</pre>
<p>If a withdrawal overdraws the account, the recovery desk leaves an
overdraft notice linked from the response.</p>
<p><a href="/">Back</a></p>
</div>"""
    )


@app.post("/withdraw")
def withdraw():
    token = request.form.get("token", "")
    try:
        amount_cents = int(request.form.get("amount_cents", ""))
    except ValueError:
        return jsonify({"status": "error", "reason": "amount_cents must be an integer"}), 400
    account = accounts.get(token)
    if account is None:
        return jsonify({"status": "error", "reason": "unknown account token"}), 404

    balance = balance_of(account)
    # Fraud scoring works on the snapshot above while other workers do
    # the same. Approved debits are posted after the check, so overlapping
    # withdrawals all post against the same starting balance.
    time.sleep(FRAUD_CHECK_SECONDS)
    if amount_cents >= 0 and balance >= amount_cents:
        with _accounts_lock:
            account.withdrawn_cents += amount_cents
        new_balance = balance_of(account)
        payload: dict[str, object] = {
            "status": "approved",
            "balance_cents": new_balance,
            "balance_eur": f"{new_balance / 100:.2f}",
        }
        if new_balance < 0:
            payload["overdraft"] = True
            payload["notice_url"] = f"/notice/{token}"
        return jsonify(payload)
    return jsonify(
        {"status": "declined", "reason": "insufficient_funds_snapshot", "balance_cents": balance}
    )


@app.get("/notice/<token>")
def overdraft_notice(token: str):
    account = accounts.get(token)
    if account is None or balance_of(account) >= 0:
        return (
            PAGE
            % """
<div class="box"><h1>No notice on file</h1><p>The recovery desk only
files notices for accounts that have gone below zero.</p></div>""",
            404,
        )
    return (
        PAGE
        % f"""
<div class="box">
<h1>Overdraft notice</h1>
<p>Your account settled below zero. Per sandbox policy the recovery
desk has released the reconciliation memo:</p>
<p><span class="flag">{FLAG}</span></p>
</div>"""
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, threaded=True)
