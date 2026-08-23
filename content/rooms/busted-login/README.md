# busted-login

Beginner guided web room. SQL injection login bypass against a
deliberately vulnerable SQLite-backed portal. Points: 100.

- `room.yaml` declares objectives, scope, safety, target, tasks.
- `lesson/` holds the learner-facing brief.
- `target/` builds the vulnerable service (Flask, port 8000).
- `solver/solver.py` proves the intended path end to end.

Verify locally with `cyberrange solve content/rooms/busted-login`.
