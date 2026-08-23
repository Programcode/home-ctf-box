# mass-assign

Easy challenge web room. Mass assignment: a JSON profile patch merges
every key into stored records, role included. Points: 150.

- `room.yaml` declares objectives, scope, safety, target, tasks.
- `lesson/` holds the learner-facing brief.
- `target/` builds the vulnerable service (Flask, port 8000).
- `solver/solver.py` proves the intended path end to end.

Verify locally with `cyberrange solve content/rooms/mass-assign`.
