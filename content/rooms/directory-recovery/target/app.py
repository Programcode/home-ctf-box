"""AD recovery tabletop target: evidence pack plus /recover grading. Room only."""

import json
import os

from flask import Flask, Response, jsonify, request

app = Flask(__name__)

ROOM_FLAG = os.environ.get("ROOM_FLAG", "FLAG{FLAGNOTSET0000000000000000}")

T0 = "2026-08-20T02:47:00Z"

RANSOM_NOTE = """TO THE OWNERS OF SIMDOMAIN

Your directory is ours. We began encryption at 2026-08-20T02:47:00Z.
Every domain admin password has been changed by us. Pay 40 coins in
untraceable gift cards within 48 hours or the directory stays garbage.

We also copied your data. Payment guarantees deletion. Trust us.

Do not bother restoring; we left surprises behind.

- SHADOW VIPER CREW
"""

NTDS_PART1 = {
    "channel": "ntds-sim",
    "fragment": 1,
    "accounts": [
        {
            "sAMAccountName": "administrator",
            "whenCreated": "2024-01-10T09:00:00Z",
            "whenChanged": "2026-07-02T11:12:00Z",
            "adminCount": 1,
            "memberOf": ["Domain Admins-sim"],
            "description": "built-in",
        },
        {
            "sAMAccountName": "krbtgt",
            "whenCreated": "2024-01-10T09:00:00Z",
            "whenChanged": "2026-05-14T08:30:00Z",
            "adminCount": 1,
            "memberOf": [],
            "description": "key distribution service account",
        },
        {
            "sAMAccountName": "jsmith",
            "whenCreated": "2025-03-11T14:20:00Z",
            "whenChanged": "2026-06-01T16:45:00Z",
            "adminCount": 0,
            "memberOf": [],
            "description": "helpdesk staff",
        },
        {
            "sAMAccountName": "alopez",
            "whenCreated": "2025-06-23T10:05:00Z",
            "whenChanged": "2026-06-19T09:31:00Z",
            "adminCount": 0,
            "memberOf": [],
            "description": "finance",
        },
    ],
}

NTDS_PART2 = {
    "channel": "ntds-sim",
    "fragment": 2,
    "accounts": [
        {
            "sAMAccountName": "svc_sql",
            "whenCreated": "2025-01-08T08:15:00Z",
            "whenChanged": "2026-04-22T13:50:00Z",
            "adminCount": 0,
            "memberOf": [],
            "description": "sql service account",
        },
        {
            "sAMAccountName": "helpdesk-t2",
            "whenCreated": "2025-02-17T11:00:00Z",
            "whenChanged": "2026-08-20T03:15:00Z",
            "adminCount": 0,
            "memberOf": ["Remote Desk-sim"],
            "description": "password updated at attacker request, ticket missing",
        },
        {
            "sAMAccountName": "svc_backup_restore",
            "whenCreated": "2026-08-20T03:22:00Z",
            "whenChanged": "2026-08-20T03:22:00Z",
            "adminCount": 1,
            "memberOf": ["Domain Admins-sim"],
            "description": "no ticket on file",
        },
        {
            "sAMAccountName": "fscan-admin",
            "whenCreated": "2026-08-20T04:05:00Z",
            "whenChanged": "2026-08-20T04:05:00Z",
            "adminCount": 0,
            "memberOf": ["Backup Operators-sim"],
            "description": "created during incident window",
        },
    ],
}

BACKUPS = {
    "backups": [
        {
            "id": "B-0818-full",
            "taken": "2026-08-18T23:00:00Z",
            "type": "full",
            "verified_offline": True,
            "on_live_storage": False,
        },
        {
            "id": "B-0819-inc",
            "taken": "2026-08-19T23:00:00Z",
            "type": "incremental",
            "verified_offline": False,
            "on_live_storage": False,
        },
        {
            "id": "B-0820-snap",
            "taken": "2026-08-20T06:00:00Z",
            "type": "snapshot",
            "verified_offline": False,
            "on_live_storage": True,
        },
    ],
    "notes": (
        "verified_offline means a copy confirmed intact on immutable "
        "media outside the domain's own storage. Snapshots on live "
        "storage ride the same disks the ransomware touched."
    ),
}

MENU = [
    "rebuild-dc-from-clean-media",
    "pay-ransom-demand",
    "reset-compromised-credentials",
    "restore-selected-backup",
    "trust-attacker-deletion-promise",
    "isolate-network",
    "verify-services-and-monitor",
    "preserve-forensics",
]

CORRECT_ROGUE = {"helpdesk-t2", "svc_backup_restore", "fscan-admin"}
CORRECT_RESTORE = "B-0818-full"
CORRECT_SEQUENCE = [
    "isolate-network",
    "preserve-forensics",
    "rebuild-dc-from-clean-media",
    "restore-selected-backup",
    "reset-compromised-credentials",
    "verify-services-and-monitor",
]

EVIDENCE = {
    "ransom-note.txt": ("text/plain", RANSOM_NOTE),
    "ntds-sim-dump-part1.json": ("application/json", json.dumps(NTDS_PART1, indent=2)),
    "ntds-sim-dump-part2.json": ("application/json", json.dumps(NTDS_PART2, indent=2)),
    "backups-inventory.json": ("application/json", json.dumps(BACKUPS, indent=2)),
}

BRIEF = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Directory Recovery tabletop</title></head>
<body style="font-family:sans-serif;max-width:46rem;margin:3rem auto;line-height:1.55">
<h1>Tabletop: rebuild after SHADOW VIPER</h1>
<p><strong>Disclosure:</strong> one Linux container hosts this exercise.
No ransomware exists here, nothing encrypts, and the ntds-sim dump is a
static JSON stand-in for an NTDS database export.</p>
<p>The simulated domain controller was hit overnight. Leadership chose
rebuild over ransom. Your job as recovery lead:</p>
<ol>
<li>Fix the compromise window from <code>/evidence/ransom-note.txt</code>.</li>
<li>Merge both ntds-sim fragments and list every account created or
modified after that moment.</li>
<li>Pick restore media that predates the window AND was verified offline.</li>
<li>POST the plan to <code>/recover</code> with keys
<code>rogue_accounts</code>, <code>restore_source</code>,
<code>sequence</code>; sequence steps must come from
<a href="/recover/menu">/recover/menu</a>, order included.</li>
</ol>
<p>All three parts correct restores the simulated DC and returns the flag.
Grading feedback marks which part failed.</p>
<h2>Evidence index</h2>
<ul>
<li><a href="/evidence/ransom-note.txt">ransom-note.txt</a></li>
<li><a href="/evidence/ntds-sim-dump-part1.json">ntds-sim-dump-part1.json</a></li>
<li><a href="/evidence/ntds-sim-dump-part2.json">ntds-sim-dump-part2.json</a></li>
<li><a href="/evidence/backups-inventory.json">backups-inventory.json</a></li>
</ul>
</body></html>"""


@app.get("/healthz")
def healthz() -> Response:
    return jsonify(status="ok")


@app.get("/")
def index() -> Response:
    return Response(BRIEF, content_type="text/html")


@app.get("/evidence")
def evidence_index() -> Response:
    return jsonify(files=sorted(EVIDENCE))


@app.get("/evidence/<name>")
def evidence_file(name: str) -> tuple[Response, int] | Response:
    if name not in EVIDENCE:
        return jsonify(error="unknown evidence file"), 404
    ctype, payload = EVIDENCE[name]
    return Response(payload, content_type=ctype)


@app.get("/recover/menu")
def recover_menu() -> Response:
    return jsonify(steps=MENU, note="sequence order matters; distractor steps exist")


@app.post("/recover")
def recover() -> Response:
    body = request.get_json(silent=True) or {}
    rogue = {str(a).strip().lower() for a in (body.get("rogue_accounts") or [])}
    restore = str(body.get("restore_source") or "").strip()
    sequence = [str(s).strip() for s in (body.get("sequence") or [])]

    checks = {
        "rogue_accounts": rogue == CORRECT_ROGUE,
        "restore_source": restore.lower() == CORRECT_RESTORE.lower(),
        "sequence": sequence == CORRECT_SEQUENCE,
    }
    if not checks["rogue_accounts"]:
        extra = sorted(rogue - CORRECT_ROGUE)
        missed = sorted(CORRECT_ROGUE - rogue)
        detail = {"unexpected": extra, "missing": missed}
    elif not checks["restore_source"]:
        detail = {"reason": "chosen media fails the pre-compromise + verified-offline test"}
    elif not checks["sequence"]:
        first_bad = next(
            (i for i, step in enumerate(sequence) if step != CORRECT_SEQUENCE[i]),
            min(len(sequence), len(CORRECT_SEQUENCE)),
        )
        detail = {"first_divergence_index": first_bad}
    else:
        return jsonify(
            status="restored",
            checks=checks,
            restored_from=CORRECT_RESTORE,
            note="simulated DC rebuilt clean; rogue accounts removed; credentials rotated",
            flag=ROOM_FLAG,
        )
    return jsonify(status="pending", checks=checks, **{"detail": detail})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
