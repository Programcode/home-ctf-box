# cloudtrail-of-crumbs

Easy challenge room opening the defense-cloud track. A deterministic
simulated cloud audit log at /evidence/cloudtrail-sim.json records a
complete credential-leak chain: a long-lived key reused from an
outside address, an assume_role call, a create_access_key minted for a
second user, and a put_bucket_policy rewrite that opened the backup
bucket to anonymous reads, followed by the anonymous downloads that
prove it. Learners separate routine sync traffic from the intrusion,
answer three exact-value questions at /report, and collect the flag.
Points: 175.

- `room.yaml` declares objectives, scope, locked target profile, one
  task with tiered hints.
- `lesson/` explains what is simulated (static JSON trail, sim.*
  namespace) versus what transfers (baseline-first analysis).
- `target/` builds a Flask box on port 8000 serving evidence and the
  report desk; nothing stateful, no egress.
- `solver/solver.py` derives all three answers from the log itself and
  files the report with httpx.

Verify locally with `cyberrange solve content/rooms/cloudtrail-of-crumbs`.
