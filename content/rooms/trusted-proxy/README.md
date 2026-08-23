# trusted-proxy

Beginner guided web room. X-Forwarded-For spoofing against a gate that
trusts forwarding headers over its own socket data. Points: 75.

- `room.yaml` declares objectives, scope, safety, target, tasks.
- `lesson/` holds the learner-facing brief.
- `target/` builds the vulnerable service (Flask, port 8000).
- `solver/solver.py` proves the intended path end to end.

Verify locally with `cyberrange solve content/rooms/trusted-proxy`.
