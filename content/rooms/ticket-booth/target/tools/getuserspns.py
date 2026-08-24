#!/usr/bin/env python3
"""getuserspns.py equivalent for the ticket-booth room (simulation).

Lists every registered SPN on the room's fake KDC and requests one
simulated service ticket per SPN. Standard library only; speaks plain
HTTP+JSON to the lab endpoint, never the real Kerberos protocol.

Usage:
    python3 getuserspns.py --kdc http://target:8000
"""

import argparse
import json
import urllib.parse
import urllib.request


def get_json(base: str, path: str):
    with urllib.request.urlopen(base + path, timeout=15) as res:
        return json.loads(res.read().decode())


def main() -> int:
    parser = argparse.ArgumentParser(prog="getuserspns")
    parser.add_argument("--kdc", required=True, help="base URL of the fake KDC")
    args = parser.parse_args()

    listing = get_json(args.kdc, "/kdc/spns")
    print(f"[simulation] {len(listing['spns'])} SPNs registered")
    for entry in listing["spns"]:
        spn = entry["spn"]
        ticket = get_json(args.kdc, f"/kdc/tgs?spn={urllib.parse.quote(spn)}")
        print(f"account: {ticket['account']}  spn: {spn}")
        print(f"  cipher:   {ticket['cipher']}")
        print(f"  enc_part: {ticket['enc_part']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
