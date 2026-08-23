# ssti-greeting

Easy challenge web room. Server-side template injection through a card
renderer that formats user input into a Jinja template string. Points: 150.

- `room.yaml` declares objectives, scope, safety, target, tasks.
- `lesson/` holds the learner-facing brief.
- `target/` builds the vulnerable service (Flask, port 8000).
- `solver/solver.py` proves the intended path end to end.

Verify locally with `cyberrange solve content/rooms/ssti-greeting`.
