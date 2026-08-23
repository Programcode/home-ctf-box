# predictable-reset

Easy challenge room. Password reset tokens are md5(username plus a
10-minute time window), so they can be forged offline for any account.
Points: 175.

- `room.yaml` declares objectives, scope, safety, target, tasks.
- `lesson/` holds the learner-facing brief.
- `target/` builds the vulnerable service (Flask, port 8000).
- `solver/solver.py` proves the intended path end to end.

Verify locally with `cyberrange solve content/rooms/predictable-reset`.
