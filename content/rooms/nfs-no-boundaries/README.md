# nfs-no-boundaries

Medium challenge Linux room. The no_root_squash lesson on a single box:
/etc/exports documents the misconfiguration, /srv/share stands in for
the writable export, and a root cron job stages a SUID-root helper into
it; learners find and execute it to read /root/flag.txt. No NFS daemon
exists. Points: 250.

- `room.yaml` declares objectives, scope, safety, target, tasks.
- `lesson/` holds the learner-facing brief, including the exact
  simulated-versus-real split.
- `target/` builds the Debian SSH box (port 22, learner/learner).
- `solver/solver.py` proves the intended path end to end with paramiko.

Verify locally with `cyberrange solve content/rooms/nfs-no-boundaries`.
