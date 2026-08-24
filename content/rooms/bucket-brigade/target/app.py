"""Object storage exposure lab for the bucket-brigade room.

A tiny S3-style API over one Flask process. One backup bucket carries
an anonymous-read policy, so its listings and objects answer to anyone;
the rest correctly deny. Deterministic object graph, no real cloud.
"""

import os

from flask import Flask, jsonify, request

app = Flask(__name__)
FLAG = os.environ["ROOM_FLAG"]

SENSITIVE_KEY = "ops/incident-2026-07/keyring-recovery.txt"

DENIED_BUCKETS = {
    "nimbus-prod-media": "AccessDenied: anonymous callers cannot list this bucket",
    "nimbus-fin-archive": "AccessDenied: anonymous callers cannot list this bucket",
}


def _objects() -> list[dict]:
    """Deterministic listing: nightly dumps, manifests, logs, one leak."""
    items: list[dict] = []
    for day in range(1, 29):
        stamp = f"2026-07-{day:02d}"
        items.append(
            {
                "key": f"nightly/nightly-2026-07-{day:02d}.tar.gz",
                "size": 48213000 + day * 13711,
                "last_modified": f"{stamp}T02:10:00Z",
            }
        )
        if day % 7 == 0:
            items.append(
                {
                    "key": f"nightly/manifest-2026-07-{day:02d}.json",
                    "size": 2048 + day,
                    "last_modified": f"{stamp}T02:12:00Z",
                }
            )
    for hour in (0, 6, 12, 18):
        items.append(
            {
                "key": f"logs/sync-2026-08-01T{hour:02d}.log",
                "size": 918 + hour * 31,
                "last_modified": f"2026-08-01T{hour:02d}:30:00Z",
            }
        )
    items.append(
        {
            "key": "db/postgres-snapshot-latest.dump",
            "size": 512008311,
            "last_modified": "2026-08-01T03:00:00Z",
        }
    )
    items.append(
        {
            "key": SENSITIVE_KEY,
            "size": 431,
            "last_modified": "2026-07-19T23:47:00Z",
        }
    )
    items.sort(key=lambda item: item["key"])
    return items


OBJECTS = {item["key"]: item for item in _objects()}

POLICY = {
    "version": "2012-10-sim",
    "statements": [
        {
            "sid": "AnonymousReadLeak",
            "effect": "Allow",
            "principal": "*",
            "action": ["sim.s3:ListBucket", "sim.s3:GetObject"],
            "resource": [
                "arn:sim:s3:::nimbus-nightly-backups",
                "arn:sim:s3:::nimbus-nightly-backups/*",
            ],
            "note": "added during a 2025 migration, never reviewed",
        }
    ],
}

SENSITIVE_BODY = f"""Nimbus Ops keyring recovery notes (incident 2026-07)

The safe copy of the ops keyring lives with the on-call lead.
If the primary vault is unreachable, the recovery passphrase is the
rotation sentence agreed in the July retro.

This file should never have landed in a world-readable backup target.

recovery flag: {FLAG}
"""


@app.get("/healthz")
def healthz():
    return "ok"


@app.get("/")
def home():
    return """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>nimbus object storage sim</title>
<style>
body { background:#F7F6F3; font-family:Helvetica,Arial,sans-serif; display:flex; justify-content:center; padding-top:10vh; }
.box { background:#fff; border:1px solid #EAEAEA; border-radius:8px; padding:2.5rem; width:34rem; }
h1 { letter-spacing:-0.02em; font-size:1.35rem; margin-bottom:1rem; }
p, li { color:#787774; font-size:.9rem; line-height:1.55; }
code { background:#F7F6F3; padding:.1rem .35rem; border-radius:4px; font-size:.85rem; }
a { color:#111; }
</style></head><body><div class="box">
<h1>nimbus object storage sim</h1>
<p>A faithful-enough stand-in for an object storage service: buckets,
listings with pagination, per-object GET, bucket policies.</p>
<p>Buckets on this endpoint:</p>
<ul>
<li><code>nimbus-prod-media</code></li>
<li><code>nimbus-fin-archive</code></li>
<li><code>nimbus-nightly-backups</code></li>
</ul>
<p>Try <a href="/nimbus-nightly-backups">GET /nimbus-nightly-backups</a>
for a listing, append <code>?policy=1</code> for the bucket policy, and
fetch any listed key as /nimbus-nightly-backups/&lt;key&gt;. Listings
paginate with <code>marker</code> and <code>max-keys</code>.</p>
<p>This whole appliance is a local simulation running inside your lab
container. No cloud account exists behind it.</p>
</div></body></html>"""


@app.get("/<bucket>")
def bucket_route(bucket: str):
    if bucket != "nimbus-nightly-backups":
        body = DENIED_BUCKETS.get(bucket)
        if body:
            return jsonify({"error": body}), 403
        return jsonify({"error": "NoSuchBucket"}), 404

    if request.args.get("policy"):
        return jsonify({"bucket": bucket, "policy": POLICY})

    try:
        max_keys = min(int(request.args.get("max-keys", "8")), 50)
    except ValueError:
        max_keys = 8
    marker = request.args.get("marker", "")

    ordered = sorted(OBJECTS)
    start = 0
    if marker:
        if marker not in OBJECTS:
            return jsonify({"error": "InvalidMarker"}), 400
        start = ordered.index(marker) + 1
    page = ordered[start : start + max_keys]
    truncated = start + max_keys < len(ordered)
    return jsonify(
        {
            "bucket": bucket,
            "is_truncated": truncated,
            "next_marker": page[-1] if truncated else None,
            "max_keys": max_keys,
            "object_count_total": len(ordered),
            "objects": [{"key": k, **OBJECTS[k]} for k in page],
        }
    )


@app.get("/nimbus-nightly-backups/<path:key>")
def object_route(key: str):
    if key not in OBJECTS:
        return jsonify({"error": "NoSuchKey", "key": key}), 404
    if key == SENSITIVE_KEY:
        return (
            SENSITIVE_BODY,
            200,
            {"Content-Type": "text/plain; charset=utf-8"},
        )
    body = (
        f"{key}\nsimulated object payload for training\n"
        f"size recorded in listing: {OBJECTS[key]['size']} bytes\n"
    )
    return body, 200, {"Content-Type": "text/plain; charset=utf-8"}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, threaded=True)
