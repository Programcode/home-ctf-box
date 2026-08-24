# Boot2Root Finale

Hard box room. The full classic arc on one target: ordered TCP port
knock, anonymously readable share page leaking live credentials,
sudo env_keep PATH escalation through an unqualified helper call.
Points: 350.

- `room.yaml` declares objectives, scope, safety, target, tasks.
- `lesson/` holds the learner-facing brief.
- `target/` builds the Debian box: sshd on 22, a knock daemon on
  4010/5011/6012 that wakes the share server on 8080, the share page
  with its leaked staff note, and the sudoers drop-in that keeps PATH
  alive for the maintenance menu script.
- `solver/solver.py` proves the whole arc end to end with raw
  sockets, httpx, paramiko, and a two-line PATH shim.

Verify locally with `cyberrange solve content/rooms/boot2root-finale`.
