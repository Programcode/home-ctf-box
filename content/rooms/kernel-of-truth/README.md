# kernel-of-truth

Hard investigation-leaning challenge room. Read the simulated
appliance's kernel version from its sysinfo API, eliminate two wrong
CVE candidates using the research notes, and drive the precompiled
exploit simulator with the one identifier that applies. Points: 275.

- `room.yaml` declares objectives, scope, safety, target, tasks.
- `lesson/` holds the learner-facing brief.
- `target/` builds the Debian box: sshd on 22 (learner/learner), a
  python3 stdlib sysinfo service on 8000, condition records plus
  NOTES.md under /opt/exploit-sim, and a small SUID-root simulator at
  /usr/local/bin/exploit-sim that contains no exploit code.
- `solver/solver.py` proves the intended path end to end: fetch the
  version from the API, read the notes over SSH, select the candidate
  whose verdict is applicable, run the simulator once.

Verify locally with `cyberrange solve content/rooms/kernel-of-truth`.
