# gpo-gone-wrong

Hard challenge Windows room on an SSH Debian box (elevated profile).
A simulated SYSVOL under /srv/sysvol-sim hosts GPO task XMLs; a root
policy loop executes each Command every 30 seconds, and one task
points into the group-writable /srv/gpo-scripts folder. Learners in
gpo-editors rewrite the script to copy the root flag. Points: 300.

- `room.yaml` declares objectives, scope, safety, target, tasks.
- `lesson/` holds the learner-facing brief.
- `target/` builds the Debian SSH box with SYSVOL-sim and policy loop.
- `solver/solver.py` proves the intended path end to end with paramiko.

Verify locally with `cyberrange solve content/rooms/gpo-gone-wrong`.
