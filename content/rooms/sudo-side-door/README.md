# sudo-side-door

Easy challenge Linux room. Passwordless sudo grant for /usr/bin/find in
/etc/sudoers.d/learner; learners escalate via find's -exec to read
/root/flag.txt. Points: 200.

- `room.yaml` declares objectives, scope, safety, target, tasks.
- `lesson/` holds the learner-facing brief.
- `target/` builds the Debian SSH box (port 22, learner/learner).
- `solver/solver.py` proves the intended path end to end with paramiko.

Verify locally with `cyberrange solve content/rooms/sudo-side-door`.
