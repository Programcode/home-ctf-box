#!/usr/bin/env python3
"""Simulated platform facts for this lab appliance.

The values printed here are the authoritative ground truth for the
room. Ambient tools such as uname report the container runtime, which
is deliberately irrelevant to the triage exercise.
"""

import sys

FACTS = [
    "KERNEL=Linux target 4.19.260-lab #1 SMP OpenRange simulated appliance "
    "Fri Aug 14 12:00:00 UTC 2026",
    "kernel-version=4.19.260",
    "userns=enabled",
    "pkexec-present=no",
    "bpf-unpriv=disabled",
]


def main() -> None:
    if len(sys.argv) == 2 and sys.argv[1] == "--json":
        import json

        facts = {}
        for line in FACTS:
            key, _, value = line.partition("=")
            facts[key] = value
        print(json.dumps(facts, indent=2))
        return
    print("sysinfo: simulated appliance facts (authoritative for this lab)")
    for line in FACTS:
        print(f"FACTS: {line}")
    print("note: container uname output does not describe the simulated platform")


if __name__ == "__main__":
    main()
