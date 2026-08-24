# registry-keys

Easy challenge Windows-track room, honestly Linux-hosted. A simulated
registry at /opt/registry (plain-text .hiv files under HKLM/HKCU
subtrees) holds autologon values under a Winlogon equivalent; the
exposed password really authenticates the adminsim account on the
container. Learners find the hive, reuse credentials via su or SSH,
and read /home/adminsim/flag.txt. Points: 175.

- `room.yaml` declares objectives, scope, safety, elevated target
  (sshd), tasks.
- `lesson/` discloses the plain-text hive stand-in and teaches why
  autologon credential storage matters.
- `target/` builds the Debian SSH box (port 22, learner/learner plus
  adminsim) with the registry tree baked in.
- `solver/solver.py` proves the intended path with paramiko: parse the
  hive values, reauthenticate, read the flag.

Verify locally with `cyberrange solve content/rooms/registry-keys`.
