# web-trail

Easy investigation SOC room. A deterministic 10000-line access log with
an SQL injection sweep and an admin login pivot, answered through a
report desk. Points: 150.

- `room.yaml` declares objectives, scope, safety, target, tasks.
- `lesson/` holds the learner-facing brief.
- `target/` builds the case service (Flask, port 8000); the log is
  generated at import time from fixed pools, no random state.
- `solver/solver.py` proves the intended log-analysis path end to end.

Verify locally with `cyberrange solve content/rooms/web-trail`.
