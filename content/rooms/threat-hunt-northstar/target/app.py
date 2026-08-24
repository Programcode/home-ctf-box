"""Northstar threat hunt: chained hypothesis stages over synthetic logs. Room target only."""

import os

from flask import Flask, Response, jsonify, request

app = Flask(__name__)
FLAG = os.environ["ROOM_FLAG"]

AUTH_LOG = """2026-08-19T00:05:11Z host=vpn-01 event=login user=alice result=success src=10.60.4.12
2026-08-19T00:06:02Z host=vpn-01 event=login user=bob result=success src=10.60.4.23
2026-08-19T00:31:45Z host=file-svc-02 event=batch user=svc-backup result=success src=10.60.9.8
2026-08-19T00:44:19Z host=vpn-01 event=login user=dana result=success src=10.60.4.51
2026-08-19T01:02:37Z host=jira-01 event=login user=alice result=success src=10.60.4.12
2026-08-19T01:15:08Z host=git-01 event=login user=bob result=success src=10.60.4.23
2026-08-19T01:38:22Z host=wiki-01 event=login user=dana result=failure src=10.60.4.51 reason=password
2026-08-19T01:38:26Z host=wiki-01 event=login user=dana result=success src=10.60.4.51
2026-08-19T02:09:41Z host=vpn-01 event=login user=svc-backup result=failure src=203.0.113.77 reason=password
2026-08-19T02:10:03Z host=vpn-01 event=login user=svc-backup result=failure src=203.0.113.77 reason=password
2026-08-19T02:10:29Z host=vpn-01 event=login user=svc-backup result=failure src=203.0.113.77 reason=password
2026-08-19T02:11:02Z host=vpn-01 event=login user=svc-backup result=failure src=203.0.113.77 reason=password
2026-08-19T02:11:44Z host=vpn-01 event=login user=svc-backup result=failure src=203.0.113.77 reason=mfa
2026-08-19T02:12:21Z host=vpn-01 event=login user=svc-backup result=failure src=203.0.113.77 reason=mfa
2026-08-19T02:13:05Z host=vpn-01 event=login user=svc-backup result=failure src=203.0.113.77 reason=mfa
2026-08-19T02:14:07Z host=vpn-01 event=login user=svc-backup result=failure src=203.0.113.77 reason=mfa
2026-08-19T02:14:52Z host=vpn-01 event=login user=svc-backup result=success src=203.0.113.77
2026-08-19T02:14:53Z host=vpn-01 event=assign ip=10.60.4.44 host=ops-wks-04 user=svc-backup
2026-08-19T02:58:36Z host=vpn-01 event=logout user=svc-backup src=203.0.113.77
2026-08-19T03:04:12Z host=file-svc-02 event=batch user=svc-backup result=success src=10.60.9.8
"""

PROXY_LOG = """2026-08-19T01:58:03Z client=10.60.4.12 GET http://intranet.billing-corp.internal/home bytes=5120 status=200
2026-08-19T02:00:41Z client=10.60.4.23 GET http://packages.internal-mirror.example/pypi/numpy bytes=1048576 status=200
2026-08-19T02:05:17Z client=10.60.4.51 GET http://time.sync.example/now bytes=120 status=200
2026-08-19T02:12:55Z client=10.60.4.23 GET http://packages.internal-mirror.example/npm/typescript bytes=2097152 status=200
2026-08-19T02:16:11Z client=10.60.4.44 GET http://files-share-fast.net/drop/q3-forecast.zip bytes=0 status=200
2026-08-19T02:22:40Z client=10.60.4.12 GET http://intranet.billing-corp.internal/reports bytes=8832 status=200
2026-08-19T02:33:29Z client=10.60.4.44 POST http://files-share-fast.net/upload bytes=48213 status=200
2026-08-19T02:36:00Z client=10.60.4.44 GET http://cdn-metrics-sync.top/api/pixel?id=7f3a91 bytes=64 status=200
2026-08-19T02:41:00Z client=10.60.4.44 GET http://cdn-metrics-sync.top/api/pixel?id=7f3a91 bytes=64 status=200
2026-08-19T02:46:00Z client=10.60.4.44 GET http://cdn-metrics-sync.top/api/pixel?id=7f3a91 bytes=64 status=200
2026-08-19T02:49:12Z client=10.60.4.51 GET http://packages.internal-mirror.example/debian/bookworm bytes=1572864 status=200
2026-08-19T02:51:00Z client=10.60.4.44 GET http://cdn-metrics-sync.top/api/pixel?id=7f3a91 bytes=64 status=200
2026-08-19T02:56:00Z client=10.60.4.44 GET http://cdn-metrics-sync.top/api/pixel?id=7f3a91 bytes=64 status=200
"""

DNS_LOG = """2026-08-19T02:00:02Z client=10.60.4.12 qname=intranet.billing-corp.internal qtype=A
2026-08-19T02:05:15Z client=10.60.4.51 qname=time.sync.example qtype=A
2026-08-19T02:12:50Z client=10.60.4.23 qname=packages.internal-mirror.example qtype=A
2026-08-19T02:17:58Z client=10.60.4.44 qname=files-share-fast.net qtype=A
2026-08-19T02:18:07Z client=10.60.4.44 qname=9f27c4ae83b65011ff02ee55cc88ab.dnsync-services.net qtype=TXT
2026-08-19T02:19:32Z client=10.60.4.44 qname=a1b2c3d4e5f60718293a4b5c6d7e8f.dnsync-services.net qtype=TXT
2026-08-19T02:21:10Z client=10.60.4.44 qname=00ff11aa22bb33cc44dd55ee66ff7701.dnsync-services.net qtype=TXT
2026-08-19T02:24:44Z client=10.60.4.44 qname=deadbeef9876543210fedcba123456ab.dnsync-services.net qtype=TXT
2026-08-19T02:27:19Z client=10.60.4.12 qname=intranet.billing-corp.internal qtype=A
2026-08-19T02:29:51Z client=10.60.4.44 qname=7731dd00442f1c8b903e6d5a2f74c9d0.dnsync-services.net qtype=TXT
2026-08-19T02:33:20Z client=10.60.4.44 qname=files-share-fast.net qtype=A
2026-08-19T02:35:55Z client=10.60.4.44 qname=cdn-metrics-sync.top qtype=A
2026-08-19T02:40:58Z client=10.60.4.51 qname=time.sync.example qtype=A
"""

STAGES = {
    1: {
        "question": (
            "Stage 1 of 5, initial access. One service account in auth.log "
            "takes a burst of failed logins and then succeeds from an "
            "address outside the 10.x internal range. Which account is it?"
        ),
        "answer": "svc-backup",
    },
    2: {
        "question": (
            "Stage 2 of 5. Which external source IP carried the failed "
            "burst and the eventual successful login for that account?"
        ),
        "answer": "203.0.113.77",
    },
    3: {
        "question": (
            "Stage 3 of 5. The vpn assignment line maps the session onto a "
            "workstation IP. Filtering proxy traffic by that IP reveals "
            "one external host used for staging, including an oversized "
            "upload. Which hostname received the upload?"
        ),
        "answer": "files-share-fast.net",
    },
    4: {
        "question": (
            "Stage 4 of 5. Exfiltration also hid inside DNS: the same "
            "workstation sent TXT queries whose first label is a long hex "
            "blob under one parent domain. Which parent domain?"
        ),
        "answer": "dnsync-services.net",
    },
    5: {
        "question": (
            "Stage 5 of 5, the beacon. One external host in the proxy log "
            "is contacted by the workstation at a metronome-steady 300 "
            "second interval. Name the C2 domain."
        ),
        "answer": "cdn-metrics-sync.top",
    },
}
FINAL_STAGE = 5


def _page(body: str) -> str:
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Threat Hunt Northstar</title>
<style>
body {{ background:#F7F6F3; font-family:Helvetica,Arial,sans-serif; display:flex; justify-content:center; padding-top:8vh; }}
.box {{ background:#fff; border:1px solid #EAEAEA; border-radius:8px; padding:2.5rem; width:31rem; }}
h1 {{ letter-spacing:-0.02em; font-size:1.4rem; margin-bottom:1rem; }}
p, li {{ color:#787774; font-size:.88rem; line-height:1.5; }}
code {{ font-family:ui-monospace,Menlo,monospace; font-size:.82rem; background:#F7F6F3; border:1px solid #EAEAEA; border-radius:4px; padding:.1rem .4rem; }}
.flag {{ background:#EDF3EC; color:#346538; border-radius:9999px; padding:.3rem 1rem; font-family:ui-monospace,Menlo,monospace; font-size:.85rem; display:inline-block; }}
</style></head><body><div class="box">{body}</div></body></html>"""


state = {"stage": 1}


@app.get("/healthz")
def healthz() -> str:
    return "ok"


@app.get("/")
def index() -> str:
    return _page(
        "<h1>Hunt Northstar</h1>"
        "<p>A billing workstation behaved like infrastructure overnight. "
        "You have three synchronized synthetic sources:</p>"
        "<ul>"
        "<li><a href='/evidence/auth.log'>/evidence/auth.log</a>, vpn and "
        "internal authentication</li>"
        "<li><a href='/evidence/proxy.log'>/evidence/proxy.log</a>, egress "
        "proxy requests</li>"
        "<li><a href='/evidence/dns.log'>/evidence/dns.log</a>, resolver "
        "queries</li>"
        "</ul>"
        "<p>The hunt desk runs a five stage hypothesis chain. Ask for your "
        "current question with GET /hunt and submit an answer with POST "
        "/hunt as JSON {'answer': '...'}. Each correct answer unlocks the "
        "next stage; finishing stage five closes the incident and prints "
        "the flag. All logs are synthetic teaching data.</p>"
    )


@app.get("/evidence/auth.log")
def auth_log() -> Response:
    return Response(AUTH_LOG, mimetype="text/plain")


@app.get("/evidence/proxy.log")
def proxy_log() -> Response:
    return Response(PROXY_LOG, mimetype="text/plain")


@app.get("/evidence/dns.log")
def dns_log() -> Response:
    return Response(DNS_LOG, mimetype="text/plain")


@app.get("/hunt")
def current_stage() -> Response:
    stage = state["stage"]
    return jsonify({"stage": stage, "question": STAGES[stage]["question"]})


@app.post("/hunt")
def submit_answer() -> Response:
    body = request.get_json(silent=True) or {}
    submitted = str(body.get("answer", "")).strip().lower()
    stage = state["stage"]
    expected = STAGES[stage]["answer"]
    if submitted != expected:
        return jsonify(
            {
                "status": "incorrect",
                "stage": stage,
                "detail": "recheck the evidence for this stage and resubmit",
            }
        )
    if stage == FINAL_STAGE:
        return jsonify(
            {
                "status": "complete",
                "summary": (
                    "Chain closed: password spray into svc-backup, VPN "
                    "session from 203.0.113.77, staging upload to "
                    "files-share-fast.net, TXT tunneling through "
                    "dnsync-services.net, and 300s beaconing to "
                    "cdn-metrics-sync.top."
                ),
                "flag": FLAG,
            }
        )
    state["stage"] += 1
    return jsonify(
        {
            "status": "correct",
            "stage": stage,
            "next_stage": state["stage"],
            "next_question": STAGES[state["stage"]]["question"],
        }
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
