# ping-of-doom

Easy challenge web room. Shell command injection through a host
diagnostics form that formats user input into a ping invocation.
Points: 200.

- `room.yaml` declares objectives, scope, safety, target, tasks.
- `lesson/` holds the learner-facing brief.
- `target/` builds the vulnerable service (Flask, port 8000).
- `solver/solver.py` proves the intended path end to end.

Verify locally with `cyberrange solve content/rooms/ping-of-doom`.
