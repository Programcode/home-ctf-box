# reused-horizon

Easy challenge crypto room. Repeating-key XOR keystream reuse broken by
crib dragging against a Flask telemetry gateway. Points: 150.

- `room.yaml` declares objectives, scope, safety, target, tasks.
- `lesson/` holds the learner-facing brief.
- `target/` builds the gateway service (Flask, port 8000).
- `solver/solver.py` proves the intended crib-drag path end to end.

Verify locally with `cyberrange solve content/rooms/reused-horizon`.
