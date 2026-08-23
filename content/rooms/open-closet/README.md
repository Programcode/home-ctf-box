# open-closet

Beginner guided web room. An unauthenticated /backups/ directory listing
exposes database dumps, and the current one embeds the vault flag in
plain SQL. Points: 50.

- `room.yaml` declares objectives, scope, safety, target, tasks.
- `lesson/` holds the learner-facing brief.
- `target/` builds the vulnerable service (Flask, port 8000).
- `solver/solver.py` proves the intended path end to end.

Verify locally with `cyberrange solve content/rooms/open-closet`.
