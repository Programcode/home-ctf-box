# tenant-trouble

Medium challenge web room. Multi-tenant invoicing where the Tenant-ID
header decides which workspace you are, so cross-tenant reads are one
header away. Points: 200.

- `room.yaml` declares objectives, scope, safety, target, tasks.
- `lesson/` holds the learner-facing brief.
- `target/` builds the vulnerable service (Flask, port 8000).
- `solver/solver.py` proves the intended path end to end.

Verify locally with `cyberrange solve content/rooms/tenant-trouble`.
