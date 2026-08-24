#!/usr/bin/env python3
"""getasreproast.py equivalent for the as-rep-arcade room (simulation).

Lists every account with pre-authentication disabled on the room's
fake KDC and requests one simulated AS-REP enc-part per account.
Standard library only; speaks plain HTTP+JSON to the lab endpoint,
never the real Kerberos protocol.

Usage:
    python3 getasreproast.py --kdc http://target:8000
"""

import argparse
import json
import urllib.parse
import urllib.request


def get_json(base: str, path: str):
    with urllib.request.urlopen(base + path, timeout=15) as res:
        return json.loads(res.read().decode())


def main() -> int:
    parser = argparse.ArgumentParser(prog="getasreproast")
    parser.add_argument("--kdc", required=True, help="base URL of the fake KDC")
    args = parser.parse_args()

    listing = get_json(args.kdc, "/users?no-preauth=1")
    users = [entry["username"] for entry in listing["users"]]
    print(f"[simulation] {len(users)} accounts with pre-auth disabled")
    for user in users:
        try:
            enc = get_json(args.kdc, f"/kdc/as?user={urllib.parse.quote(user)}")
        except Exception as exc:  # noqa: BLE001 - lab tool prints and continues
            print(f"user: {user}")
            print(f"  error:   request failed ({exc})")
            continue
        print(f"user: {enc['user']}")
        print(f"  cipher:   {enc['cipher']}")
        print(f"  enc_part: {enc['enc_part']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
