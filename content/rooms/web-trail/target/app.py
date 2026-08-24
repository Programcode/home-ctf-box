"""Case file for the storefront intrusion. Room target only.

The access log is generated deterministically at import time from fixed
pools and index arithmetic, so every restart produces identical bytes.
No real traffic is involved anywhere.
"""

import os
from datetime import datetime, timezone

from flask import Flask, Response, request

app = Flask(__name__)
FLAG = os.environ["ROOM_FLAG"]

SQLI_IP = "203.0.113.77"
PIVOT_IP = "198.51.100.23"
LOGIN_AGENT = "python-requests/2.31.0"

BASE_TS = int(datetime(2026, 8, 14, 0, 0, 0, tzinfo=timezone.utc).timestamp())
TOTAL_LINES = 10_000

PATHS = (
    "/",
    "/index.html",
    "/static/app.js",
    "/static/styles.css",
    "/api/products",
    "/api/products?category=books",
    "/cart",
    "/checkout/address",
    "/favicon.ico",
    "/search?q=archive",
    "/help/shipping",
    "/about",
)
IPS = tuple(f"10.40.{2 + i // 8}.{18 + (i * 5) % 40}" for i in range(16))
UAS = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:127.0) Gecko/20100101 Firefox/127.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148 Safari/604.1",
)
SQLI_PAYLOADS = (
    "/product.php?id=1%20ORDER%20BY%205--",
    "/product.php?id=1%27%20ORDER%20BY%207--",
    "/product.php?id=-1%27%20UNION%20SELECT%20NULL,NULL,NULL,NULL,NULL,NULL,NULL--",
    "/product.php?id=-1%27%20UNION%20SELECT%20NULL,version(),NULL,NULL,NULL,NULL,NULL--",
    "/product.php?id=-1%27%20UNION%20SELECT%20NULL,user(),NULL,NULL,NULL,NULL,NULL--",
    "/product.php?id=-1%27%20UNION%20SELECT%20NULL,table_name,NULL,NULL,NULL,NULL,NULL%20FROM%20information_schema.tables--",
    "/product.php?id=-1%27%20UNION%20SELECT%20NULL,password,NULL,NULL,NULL,NULL,NULL%20FROM%20users--",
    "/product.php?id=1%27%20AND%20SLEEP(3)--",
)
STUFF_USERS = ("admin", "root", "administrator")


def _fmt_ts(seconds: int) -> str:
    dt = datetime.fromtimestamp(seconds, tz=timezone.utc)
    return dt.strftime("%d/%b/%Y:%H:%M:%S +0000")


def _line(ip: str, ts: int, method: str, path: str, status: int, size: int, ua: str) -> str:
    return f'{ip} - - [{_fmt_ts(ts)}] "{method} {path} HTTP/1.1" {status} {size} "-" "{ua}"'


def build_log() -> str:
    lines = []
    for i in range(TOTAL_LINES):
        ts = BASE_TS + i * 3
        if 3000 <= i < 3156:
            status = 200 if i % 2 == 0 else 403
            lines.append(
                _line(
                    SQLI_IP,
                    ts,
                    "GET",
                    SQLI_PAYLOADS[i % len(SQLI_PAYLOADS)],
                    status,
                    512 + (i % 7),
                    "sqlmap/1.7.11#stable (http://sqlmap.org)",
                )
            )
            continue
        if 5200 <= i < 5244:
            user = STUFF_USERS[i % len(STUFF_USERS)]
            lines.append(_line(SQLI_IP, ts, "POST", f"/login?user={user}", 401, 231, LOGIN_AGENT))
            continue
        if i == 5300:
            lines.append(_line(PIVOT_IP, ts, "POST", "/login?user=admin", 302, 0, LOGIN_AGENT))
            continue
        if i == 5301:
            lines.append(_line(PIVOT_IP, ts, "GET", "/admin/exports", 200, 48112, LOGIN_AGENT))
            continue

        path = PATHS[i % len(PATHS)]
        if i % 9 == 0:
            status = 304
        elif i % 23 == 0:
            status = 404
        else:
            status = 200
        size = ((i * 137) % 40_000) + 300
        lines.append(_line(IPS[i % len(IPS)], ts, "GET", path, status, size, UAS[i % len(UAS)]))
    return "\n".join(lines) + "\n"


LOG_TEXT = build_log()

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Case 2026-08-14: storefront night shift</title>
<style>
body { background:#F7F6F3; font-family:Helvetica,Arial,sans-serif; display:flex; justify-content:center; padding-top:12vh; }
.box { background:#fff; border:1px solid #EAEAEA; border-radius:8px; padding:2.5rem; width:34rem; }
h1 { letter-spacing:-0.02em; font-size:1.35rem; margin-bottom:1rem; }
p, li { color:#787774; font-size:.9rem; line-height:1.55; }
code { background:#F7F6F3; padding:.1rem .35rem; border-radius:4px; font-size:.85rem; }
.flag { background:#EDF3EC; color:#346538; border-radius:9999px; padding:.35rem 1rem; display:inline-block; }
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
<h1>Case 2026-08-14: storefront night shift</h1>
<p>The front door of the Meridian Archive storefront logged one full
night of traffic, ten thousand requests. Somewhere in there an intruder
swept the product pages with an injection tool, threw passwords at the
login form, and finally signed in to the admin area from new
infrastructure.</p>
<p>Evidence: <a href="/evidence/access.log">access.log</a>
(Apache combined format, 10000 lines).</p>
<p>The incident report takes three answers by POST to /report as JSON:
<code>sqli_ip</code>, <code>account</code>, and
<code>login_agent</code>. All three correct closes the case.</p>
</div>"""
    )


@app.get("/evidence/access.log")
def evidence():
    return Response(
        LOG_TEXT,
        mimetype="text/plain",
        headers={"Content-Disposition": "attachment; filename=access.log"},
    )


@app.post("/report")
def report():
    body = request.get_json(silent=True) or {}
    got = {
        "sqli_ip": str(body.get("sqli_ip", "")).strip(),
        "account": str(body.get("account", "")).strip(),
        "login_agent": str(body.get("login_agent", "")).strip(),
    }
    want = {"sqli_ip": SQLI_IP, "account": "admin", "login_agent": LOGIN_AGENT}
    wrong = sorted(k for k, v in want.items() if got[k] != v)
    if wrong:
        return {"result": "rejected", "wrong_keys": wrong}, 403
    return {"result": "accepted", "flag": FLAG}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, threaded=True)
