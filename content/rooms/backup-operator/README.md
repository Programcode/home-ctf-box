# backup-operator

Medium challenge Windows-AD-flavored room on an elevated Debian SSH
box (port 22, learner/learner). The learner sits in group backup, which
may execute /usr/local/bin/disk-shadow-sim (SUID root, mode 4750), a
compiled helper that stages a copy of any named file under /tmp,
simulating SeBackupPrivilege. Learners copy /root/flag.txt and read the
staged copy. Points: 250.

- `room.yaml` declares objectives, scope, safety, target, tasks.
- `lesson/` holds the learner-facing brief.
- `target/` builds the SSH box; `disk-shadow-sim.c` compiles at image build.
- `solver/solver.py` proves the intended path end to end with paramiko.

Verify locally with `cyberrange solve content/rooms/backup-operator`.
