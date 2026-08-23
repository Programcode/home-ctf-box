# cache-me-outside

Hard challenge web room. Cache poisoning against a path-keyed page
cache that ignores host routing headers; internal hosts render a deploy
banner holding the flag. Points: 275.

- `room.yaml` declares objectives, scope, safety, target, tasks.
- `lesson/` holds the learner-facing brief.
- `target/` builds the vulnerable service (Flask, port 8000).
- `solver/solver.py` proves the intended path end to end.

Verify locally with `cyberrange solve content/rooms/cache-me-outside`.
