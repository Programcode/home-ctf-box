# Double Trouble

Easy challenge room. Cartly validates the first discount parameter but
charges the last, so a repeated parameter passes inspection with an
honest value and pays with a generous one. Points: 150.

- `room.yaml` declares objectives, scope, safety, target, tasks.
- `lesson/` holds the learner-facing brief.
- `target/` builds the vulnerable service (Flask, port 8000).
- `solver/solver.py` proves the intended path end to end.

Verify locally with `cyberrange solve content/rooms/double-trouble`.
