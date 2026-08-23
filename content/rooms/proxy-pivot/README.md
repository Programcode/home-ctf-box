# proxy-pivot

Hard challenge room. SSH into the target, then pivot to an admin
console bound to its loopback interface with a local forward. Points: 275.

- `room.yaml` declares objectives, scope, safety, target, tasks.
- `lesson/` holds the learner-facing brief.
- `target/` builds the Debian box: sshd on 22 (learner/learner) plus a
  python3 stdlib console bound to 127.0.0.1:9001 only.
- `solver/solver.py` proves the intended end-to-end path with a
  paramiko direct-tcpip channel and hand-written HTTP bytes.

Verify locally with `cyberrange solve content/rooms/proxy-pivot`.
