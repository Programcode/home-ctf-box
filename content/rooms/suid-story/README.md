# suid-story

Easy challenge Linux room. Custom SUID-root binary
`/usr/local/bin/reportgen` whose --dump mode runs
`/bin/cat /root/flag.txt`; learners find it via `find / -perm -4000`
and run it. Points: 225.

- `room.yaml` declares objectives, scope, safety, target, tasks.
- `lesson/` holds the learner-facing brief.
- `target/` builds the Debian SSH box (port 22, learner/learner).
- `solver/solver.py` proves the intended path end to end with paramiko.

Verify locally with `cyberrange solve content/rooms/suid-story`.
