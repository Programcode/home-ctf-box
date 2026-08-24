# memory-lane

Medium investigation DFIR room. Synthetic process listing plus strings
excerpts from a memory capture: injected process, dead-parent anomaly,
and C2 domain, reported as one triple. Points: 250.

- `room.yaml` declares objectives, scope, safety, target, tasks.
- `lesson/` holds the learner-facing brief.
- `target/` builds the lab desk (Flask, port 8000) serving both static
  evidence files and the report endpoint.
- `solver/solver.py` proves the intended analysis path end to end.

Verify locally with `cyberrange solve content/rooms/memory-lane`.
