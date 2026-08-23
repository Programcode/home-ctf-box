# cartographer

Easy challenge web room. API discovery against a Flask site that leaks
its internal admin plane through robots.txt and an OpenAPI document.
Points: 150.

- `room.yaml` declares objectives, scope, safety, target, tasks.
- `lesson/` holds the learner-facing brief.
- `target/` builds the vulnerable service (Flask, port 8000).
- `solver/solver.py` proves the intended path end to end.

Verify locally with `cyberrange solve content/rooms/cartographer`.
