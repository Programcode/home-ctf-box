# bucket-brigade

Easy challenge room continuing the defense-cloud track. A local
S3-style Flask API serves three buckets; two deny anonymous callers
and one, nimbus-nightly-backups, honors anonymous listing and object
reads thanks to an unreviewed wildcard policy statement. Learners
confirm the misconfiguration via ?policy=1, walk the 38-object
listing through marker pagination, spot
ops/incident-2026-07/keyring-recovery.txt among routine backups, and
download it for the flag. Points: 150.

- `room.yaml` declares objectives, scope, locked profile, one task
  with tiered hints.
- `lesson/` teaches baseline-versus-anomaly thinking for storage
  policies and honest simulation disclosure.
- `target/` builds the Flask appliance on port 8000 with deterministic
  object graph and paginated listings.
- `solver/solver.py` follows next_marker until truncation ends, picks
  the sensitive key, and extracts the flag with httpx.

Verify locally with `cyberrange solve content/rooms/bucket-brigade`.
