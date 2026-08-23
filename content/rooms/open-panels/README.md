# open-panels

Beginner guided web room. An undocumented /debug panel on a status
board prints the process environment, flag included, to unauthenticated
visitors. Points: 50.

- `room.yaml` declares objectives, scope, safety, target, tasks.
- `lesson/` holds the learner-facing brief.
- `target/` builds the vulnerable service (Flask, port 8000).
- `solver/solver.py` proves the intended path end to end.

Verify locally with `cyberrange solve content/rooms/open-panels`.
