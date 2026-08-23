# packet-diary

Easy investigation room. Synthetic FTP capture served as evidence; the
leaked cleartext password unlocks the case report. Points: 125.

- `room.yaml` declares objectives, scope, safety, target, tasks.
- `lesson/` holds the learner-facing brief.
- `target/` builds the case file app (Flask on 8000) which generates a
  deterministic libpcap byte stream in-process at startup.
- `solver/solver.py` proves the intended path end to end: download,
  find the PASS line, submit to /report.

Verify locally with `cyberrange solve content/rooms/packet-diary`.
