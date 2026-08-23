# xxe-importer

Medium challenge web room. XML external entity injection against a
legacy-style importer that resolves external entities. Points: 225.

- `room.yaml` declares objectives, scope, safety, target, tasks.
- `lesson/` holds the learner-facing brief.
- `target/` builds the vulnerable service (Flask, port 8000) and writes
  the flag to `/flag.txt` at startup so the XXE has something to read.
- `solver/solver.py` proves the intended path end to end.

Verify locally with `cyberrange solve content/rooms/xxe-importer`.
