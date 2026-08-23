# paper-permissions

Beginner guided Linux room. A root loop copies its mode-600 config to a
world-readable /var/backups/app.conf every 30 seconds; learners find and
read the copy. Points: 100.

- `room.yaml` declares objectives, scope, safety, target, tasks.
- `lesson/` holds the learner-facing brief.
- `target/` builds the Debian SSH box (port 22, learner/learner).
- `solver/solver.py` proves the intended path end to end with paramiko.

Verify locally with `cyberrange solve content/rooms/paper-permissions`.
