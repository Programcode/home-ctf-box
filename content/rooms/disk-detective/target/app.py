"""Case file for the compromised host timeline. Room target only.

The body file is generated deterministically at import time from fixed
pools and epoch arithmetic; no real forensic image exists.
"""

import os
from datetime import datetime, timezone

from flask import Flask, Response, request

app = Flask(__name__)
FLAG = os.environ["ROOM_FLAG"]

DELETED_NAME = "/var/tmp/.cleanup.sh (deleted)"
PERSISTENCE_PATH = "/etc/cron.d/system-health-sync"


def _epoch(day: int, hour: int, minute: int, second: int) -> int:
    return int(datetime(2026, 8, day, hour, minute, second, tzinfo=timezone.utc).timestamp())


# (name, uid, gid, mode, size_base)
BASELINE_FILES = (
    ("/etc/hostname", 0, 0, "r/rrw-r--r--", 14),
    ("/etc/hosts", 0, 0, "r/rrw-r--r--", 221),
    ("/etc/passwd", 0, 0, "r/rrw-r--r--", 1645),
    ("/etc/shadow", 0, 42, "r/rr--------", 1013),
    ("/etc/crontab", 0, 0, "r/rrw-r--r--", 722),
    ("/etc/apt/sources.list", 0, 0, "r/rrw-r--r--", 1188),
    ("/var/log/syslog", 0, 4, "r/rrw-r-----", 184320),
    ("/var/log/auth.log", 0, 4, "r/rrw-r-----", 96768),
    ("/var/log/kern.log", 0, 0, "r/rrw-r-----", 51200),
    ("/var/lib/dpkg/status", 0, 0, "r/rrw-r--r--", 983040),
    ("/home/deploy/.bashrc", 1001, 1001, "r/rrw-r--r--", 3771),
    ("/home/deploy/.profile", 1001, 1001, "r/rrw-r--r--", 807),
    ("/home/deploy/.ssh/authorized_keys", 1001, 1001, "r/rrw-------", 569),
    ("/home/deploy/notes/standup.md", 1001, 1001, "r/rrw-r--r--", 2143),
    ("/usr/bin/sshd", 0, 0, "r/rrwxr-xr-x", 996352),
    ("/usr/bin/sudo", 0, 0, "r/rrwsr-xr-x", 599776),
    ("/usr/sbin/nginx", 0, 0, "r/rrwxr-xr-x", 1212544),
    ("/usr/local/bin/metrics-agent", 0, 0, "r/rrwxr-xr-x", 28672),
    ("/var/cache/apt/archives/partial", 0, 0, "d/drwxr-xr-x", 4096),
    ("/tmp/systemd-private-1001/cache", 1001, 1001, "d/drwx------", 4096),
    ("/srv/archive/manifest-2026-08.txt", 1001, 1001, "r/rrw-r--r--", 44210),
    ("/opt/reporting/outbox.lock", 0, 0, "r/rrw-r--r--", 0),
)

WINDOW_FILES = (
    (_epoch(14, 2, 31, 5), "/tmp/update.tar.gz", 0, 0, "r/rrw-r--r--", 481233),
    (_epoch(14, 2, 33, 40), "/home/deploy/.ssh/authorized_keys", 1001, 1001, "r/rrw-------", 1103),
    (_epoch(14, 2, 38, 11), DELETED_NAME, 1001, 1001, "r/rrwxr-xr-x", 384),
    (_epoch(14, 2, 41, 22), "/var/log/auth.log", 0, 4, "r/rrw-r-----", 0),
    (_epoch(14, 2, 47, 58), "/usr/local/bin/.sync-helper", 0, 0, "r/rrwxr-xr-x", 27408),
    (_epoch(14, 2, 52, 47), PERSISTENCE_PATH, 0, 0, "r/rrw-r--r--", 142),
    (_epoch(14, 3, 1, 30), "/var/tmp/agent.sock", 1001, 1001, "s/srw-rw----", 0),
    (_epoch(14, 3, 12, 9), "/var/log/wtmp", 0, 22, "r/rrw-rw-r--", 460800),
)


def build_timeline() -> str:
    rows = []
    for day in (12, 13, 14, 15, 16):
        baseline_count = 44 if day == 14 else 132
        for i in range(baseline_count):
            index = i % len(BASELINE_FILES)
            name, uid, gid, mode, size = BASELINE_FILES[index]
            ts = _epoch(day, 0, 0, 0) + (i * 601 + day * 37) % 86400
            inode = 200_000 + index * 11
            rows.append((ts, f"0|{name}|{inode}|{mode}|{uid}|{gid}|{size}|{ts}|{ts}|{ts}|0"))

    for ts, name, uid, gid, mode, size in WINDOW_FILES:
        inode = 300_000 + ts % 10_000
        crtime = ts if "(deleted)" in name or name.startswith("/etc/cron.d/") else 0
        rows.append((ts, f"0|{name}|{inode}|{mode}|{uid}|{gid}|{size}|{ts}|{ts}|{ts}|{crtime}"))

    rows.sort(key=lambda row: row[0])
    return "\n".join(row[1] for row in rows) + "\n"


TIMELINE_TEXT = build_timeline()

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Case 2026-08-14: host timeline carve</title>
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
<h1>Case 2026-08-14: host timeline carve</h1>
<p>Before the compromised host was rebuilt, the imaging rig carved a
filesystem timeline and the lab saved it as a mactime-style body file:
eleven pipe-separated columns per row, sorted by modification time,
five days around the intrusion.</p>
<p>Evidence: <a href="/evidence/timeline.csv">timeline.csv</a>
(TSK body format).</p>
<p>The lab desk accepts two findings by POST to /report as JSON under
the key <code>findings</code>: first the deleted-file hint exactly as
its name appears in the timeline, second the persistence artifact path.
Chronological order is part of the report. Correct findings close the
case.</p>
</div>"""
    )


@app.get("/evidence/timeline.csv")
def evidence():
    return Response(
        TIMELINE_TEXT,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=timeline.csv"},
    )


@app.post("/report")
def report():
    body = request.get_json(silent=True) or {}
    findings = body.get("findings")
    if not isinstance(findings, list) or len(findings) != 2:
        return {"result": "rejected", "error": "findings must be a two-element list"}, 403
    got = [str(item).strip() for item in findings]
    want = [DELETED_NAME, PERSISTENCE_PATH]
    wrong = [i for i, pair in enumerate(zip(got, want, strict=False)) if pair[0] != pair[1]]
    if wrong:
        return {"result": "rejected", "wrong_positions": wrong}, 403
    return {"result": "accepted", "flag": FLAG}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, threaded=True)
