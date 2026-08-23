# token-forger

Medium challenge web room. JWT algorithm-confusion forgery against a
service whose verifier trusts the token header. Points: 250.

- `room.yaml` declares objectives, scope, safety, target, tasks.
- `lesson/` holds the learner-facing brief.
- `target/` builds the vulnerable service (Flask, port 8000).
- `solver/solver.py` proves the intended path end to end.

Verify locally with `cyberrange solve content/rooms/token-forger`.
