#!/usr/bin/python3
"""Policy loop for the gpo-gone-wrong room (simulation).

Reads every Tasks XML under /srv/sysvol-sim the way real Group Policy
processing reads scheduled-task definitions from SYSVOL, then executes
each Command as root on its stated interval. Runs forever from the
container entrypoint.
"""

import glob
import subprocess
import time
import xml.etree.ElementTree as ET
from datetime import datetime

POLL_SECONDS = 30


def interval_seconds(raw: str) -> int:
    # Minimal ISO-8601 duration support for PTnS/PTnM forms in this room.
    seconds = POLL_SECONDS
    if raw.startswith("PT"):
        number = ""
        for char in raw[2:]:
            if char.isdigit():
                number += char
            elif char == "S":
                seconds = int(number or POLL_SECONDS)
                break
            elif char == "M":
                seconds = int(number or 1) * 60
                number = ""
    return max(seconds, 5)


def collect_tasks() -> list[tuple[str, int]]:
    tasks: list[tuple[str, int]] = []
    pattern = "/srv/sysvol-sim/Policies/*/Machine/Preferences/Tasks/*.xml"
    for path in sorted(glob.glob(pattern)):
        try:
            tree = ET.parse(path)
        except ET.ParseError:
            print(f"[gpo-sim] skipping unparseable {path}", flush=True)
            continue
        root = tree.getroot()
        for props in root.iter("Properties"):
            command_el = props.find("Command")
            if command_el is None or not (command_el.text or "").strip():
                continue
            interval = interval_seconds(props.get("interval", ""))
            stamp = datetime.now().strftime("%H:%M:%S")
            print(
                f"[gpo-sim] {stamp} task {props.get('name')!r} -> {command_el.text.strip()}",
                flush=True,
            )
            tasks.append((command_el.text.strip(), interval))
    return tasks


def main() -> int:
    print("[gpo-sim] policy loop started", flush=True)
    while True:
        for command, _interval in collect_tasks():
            try:
                result = subprocess.run(["/bin/sh", "-c", command])
                if result.returncode != 0:
                    print(f"[gpo-sim] task failed rc={result.returncode}: {command}", flush=True)
            except OSError as exc:
                print(f"[gpo-sim] task error: {exc}", flush=True)
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    raise SystemExit(main())
