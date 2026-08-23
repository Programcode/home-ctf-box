# scheduled-surprise

Easy challenge Linux room. Group-writable /usr/local/sbin plus a root
cron job running /usr/local/sbin/cleanup.sh every minute; learners swap
the script to copy /root/flag.txt to /tmp/flag and wait for cron.
Points: 175.

- `room.yaml` declares objectives, scope, safety, target, tasks.
- `lesson/` holds the learner-facing brief.
- `target/` builds the Debian SSH box (port 22, learner/learner).
- `solver/solver.py` proves the intended path end to end with paramiko.

Verify locally with `cyberrange solve content/rooms/scheduled-surprise`.
