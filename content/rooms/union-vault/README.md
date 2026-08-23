# union-vault

Easy challenge room. UNION-based SQL injection against a two-column
product search extracts a flag from a vault table in the same SQLite
database. Points: 225.

- `room.yaml` declares objectives, scope, safety, target, tasks.
- `lesson/` holds the learner-facing brief.
- `target/` builds the vulnerable service (Flask, port 8000).
- `solver/solver.py` proves the intended path end to end.

Verify locally with `cyberrange solve content/rooms/union-vault`.
