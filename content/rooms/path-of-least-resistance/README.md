# path-of-least-resistance

Easy challenge Linux room. The SUID-root helper /usr/local/bin/backupctl
calls tar with no absolute path, so PATH decides who answers; learners
plant their own tar in a writable PATH directory and read /root/flag.txt
as root. Points: 175.

- `room.yaml` declares objectives, scope, safety, target, tasks.
- `lesson/` holds the learner-facing brief.
- `target/` builds the Debian SSH box (port 22, learner/learner).
- `solver/solver.py` proves the intended path end to end with paramiko.

Verify locally with `cyberrange solve content/rooms/path-of-least-resistance`.
