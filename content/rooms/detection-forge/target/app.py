"""Detection forge: validate authored rules against fixed fixture sets. Room target only."""

import json
import os
import re

from flask import Flask, Response, jsonify, request

app = Flask(__name__)
FLAG = os.environ["ROOM_FLAG"]
MAX_PATTERN_LENGTH = 400

RULES = {
    "sqli-union-select": {
        "title": "Union-based SQL injection in query strings",
        "positives": [
            "/items.php?id=1 UNION SELECT username, password FROM users--",
            "q=electronics' UNION SELECT * FROM orders--",
            "?cat=2 UNION ALL SELECT NULL,NULL,SLEEP(5)",
            "id=7+UNION+SELECT+card_number+FROM+payments",
        ],
        "negatives": [
            "reunion selection committee minutes 2026",
            "SELECT * FROM inventory WHERE active = true",
            "?q=union+jack+flag+shop",
            "UNIONIZED workers select new representatives",
        ],
    },
    "path-traversal": {
        "title": "Repeated or encoded dot-dot traversal sequences",
        "positives": [
            "GET /download?file=../../../../etc/passwd",
            "path=%2e%2e%2f%2e%2e%2fetc%2fpasswd",
            "..\\..\\windows\\system32\\config\\sam",
            "download=../../../root/.ssh/id_rsa",
        ],
        "negatives": [
            "report=2024..2025_annual_summary.pdf",
            "GET /docs/../index.html",
            "notes/dir/sub/file.txt",
            "price=10..20&range=fair",
        ],
    },
    "exfil-base64-param": {
        "title": "Long base64 payloads in short exfil parameters",
        "positives": [
            "GET /export?d=YWRtaW46c3VwZXJzZWNyZXQ=",
            "&c=dG91Y2ggL3RtcC9wd25lZA==",
            "?blob=U29sIFNheWVyIHdhcyBoZXJlIQ==",
            "GET /relay?d=eJx9aGVsbG8gd29ybGQgbWFya2Vy",
        ],
        "negatives": [
            "?d=hello-world",
            "&color=%23ffffff",
            "?data=abc123&id=abcdefgh12345678",
            "?session=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",
        ],
    },
    "dns-tunnel-label": {
        "title": "DNS names carrying oversized tunnel labels",
        "positives": [
            "9f27d4c1ae83b65011ff02ee55cc88ab7731dd0044.n.update.example-corp.net",
            "MZQW43LFOJRGS43ZM5XCA3DFEB2GK3TUFVRSG4YA.t.exfil-zone.example",
            "aabbccddeeff00112233445566778899aabbccdd.beacon.c2-relay.example.org",
        ],
        "negatives": [
            "www.example-corp.net",
            "intranet-portal.finance.example-corp.net",
            "cdn-payload-hashes.d982fa1c.blob.example.net",
            "status-check-prod.eu-west-1.aws.internal",
        ],
    },
}

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Detection Forge</title>
<style>
body { background:#F7F6F3; font-family:Helvetica,Arial,sans-serif; display:flex; justify-content:center; padding-top:8vh; }
.box { background:#fff; border:1px solid #EAEAEA; border-radius:8px; padding:2.5rem; width:31rem; }
h1 { letter-spacing:-0.02em; font-size:1.4rem; margin-bottom:1rem; }
p, li { color:#787774; font-size:.88rem; line-height:1.5; }
code, pre { font-family:ui-monospace,Menlo,monospace; font-size:.82rem; background:#F7F6F3; border:1px solid #EAEAEA; border-radius:4px; padding:.1rem .4rem; }
pre { padding:.9rem; overflow:auto; white-space:pre-wrap; }
</style></head><body>{BODY}</body></html>"""


def page(body: str) -> str:
    return PAGE.replace("{BODY}", body)


@app.get("/healthz")
def healthz() -> str:
    return "ok"


@app.get("/")
def index() -> str:
    return page(
        '<div class="box"><h1>Detection forge</h1>'
        "<p>Four rule slots are open this week. The labeled trace bundle "
        "lives at <a href='/evidence/traces.json'>/evidence/traces.json</a>: "
        "each rule id carries positives the rule must match and negatives "
        "it must never match.</p>"
        "<p>Submit the complete ruleset:</p>"
        "<pre>POST /forge\n"
        '{"rules": {"sqli-union-select": "...", "path-traversal": "...",'
        '\n           "exfil-base64-param": "...", "dns-tunnel-label": "..."}}</pre>'
        "<p>Evaluation compiles each pattern case insensitively with search "
        "semantics against every fixture. A rule passes only when all "
        "positives fire and no negative does. Patterns cap at 400 "
        "characters. All four passing returns the flag.</p>"
        "<p>All traces are synthetic strings for authoring practice; "
        "nothing here is live traffic or executable content.</p></div>"
    )


@app.get("/evidence/traces.json")
def traces() -> Response:
    bundle = {}
    for rid, block in RULES.items():
        bundle[rid] = {
            "title": block["title"],
            "evaluation": "re.search with re.IGNORECASE; pass = all positives matched, no negative matched",
            "positives": block["positives"],
            "negatives": block["negatives"],
        }
    return Response(json.dumps(bundle, indent=2), mimetype="application/json")


def _evaluate(pattern_text: str, rid: str) -> dict:
    if len(pattern_text) > MAX_PATTERN_LENGTH:
        return {"pass": False, "error": f"pattern exceeds {MAX_PATTERN_LENGTH} characters"}
    try:
        pattern = re.compile(pattern_text, re.IGNORECASE)
    except re.error as exc:
        return {"pass": False, "error": f"invalid regex: {exc}"}
    missed = [s for s in RULES[rid]["positives"] if not pattern.search(s)]
    false_positives = [s for s in RULES[rid]["negatives"] if pattern.search(s)]
    return {
        "pass": not missed and not false_positives,
        "matched_positives": len(RULES[rid]["positives"]) - len(missed),
        "positives_total": len(RULES[rid]["positives"]),
        "missed_positives": missed,
        "false_positives": false_positives,
        "error": None,
    }


@app.post("/forge")
def forge() -> Response:
    body = request.get_json(silent=True) or {}
    submitted = body.get("rules")
    if not isinstance(submitted, dict):
        return jsonify({"error": "body must be {'rules': {rule_id: pattern}}"}), 400

    unknown = sorted(set(submitted) - set(RULES))
    if unknown:
        return jsonify({"error": f"unknown rule ids: {', '.join(unknown)}"}), 400
    missing = sorted(set(RULES) - set(submitted))
    if missing:
        return jsonify({"error": f"missing rule ids: {', '.join(missing)}"}), 400

    results = {rid: _evaluate(str(pattern), rid) for rid, pattern in submitted.items()}
    solved = all(r["pass"] for r in results.values())
    return jsonify(
        {
            "results": results,
            "solved": solved,
            "flag": FLAG if solved else None,
        }
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
