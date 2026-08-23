# first-shell

Beginner guided Linux room. Plain SSH login as the learner account,
home-directory enumeration, and reading a learner-owned flag file.
Points: 75.

- `room.yaml` declares objectives, scope, safety, target, tasks.
- `lesson/` holds the learner-facing brief.
- `target/` builds the Debian SSH box (port 22, learner/learner).
- `solver/solver.py` proves the intended path end to end with paramiko.

Verify locally with `cyberrange solve content/rooms/first-shell`.
