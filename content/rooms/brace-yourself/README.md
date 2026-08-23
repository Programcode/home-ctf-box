# brace-yourself

Easy challenge web room. Format string injection through a greeting
endpoint that formats user input with server-side context. Points: 125.

- `room.yaml` declares objectives, scope, safety, target, tasks.
- `lesson/` holds the learner-facing brief.
- `target/` builds the vulnerable service (Flask, port 8000).
- `solver/solver.py` proves the intended path end to end.

Verify locally with `cyberrange solve content/rooms/brace-yourself`.
