# wrong-method

Beginner guided web room. Verb tampering: GET is blocked on the admin
console while PUT and DELETE pass the same handler. Points: 75.

- `room.yaml` declares objectives, scope, safety, target, tasks.
- `lesson/` holds the learner-facing brief.
- `target/` builds the vulnerable service (Flask, port 8000).
- `solver/solver.py` proves the intended path end to end.

Verify locally with `cyberrange solve content/rooms/wrong-method`.
