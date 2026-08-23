# cookie-shapeshifter

Beginner guided web room. Unsigned base64 JSON cookie forgery against a
loyalty portal that trusts client-side identity. Points: 100.

- `room.yaml` declares objectives, scope, safety, target, tasks.
- `lesson/` holds the learner-facing brief.
- `target/` builds the vulnerable service (Flask, port 8000).
- `solver/solver.py` proves the intended path end to end.

Verify locally with `cyberrange solve content/rooms/cookie-shapeshifter`.
