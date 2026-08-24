# disk-detective

Medium investigation DFIR room. A deterministic mactime-style body
file around an intrusion window: deleted-file hint plus persistence
artifact, reported in chronological order. Points: 275.

- `room.yaml` declares objectives, scope, safety, target, tasks.
- `lesson/` holds the learner-facing brief.
- `target/` builds the lab desk (Flask, port 8000); the timeline is
  generated at import time from fixed epochs and pools.
- `solver/solver.py` proves the intended timeline-analysis path.

Verify locally with `cyberrange solve content/rooms/disk-detective`.
