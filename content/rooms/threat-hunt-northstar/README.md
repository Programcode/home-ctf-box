# Threat Hunt Northstar

Hard investigation threat-hunting room. Pivot through synthetic auth,
proxy, and DNS telemetry along a five stage hypothesis chain from
password spray to a metronome-steady C2 beacon. Points: 300.

- `room.yaml` declares objectives, scope, safety, target, tasks.
- `lesson/` holds the learner-facing brief.
- `target/` builds the hunt desk and three log sources (Flask, port 8000).
- `solver/solver.py` derives every answer analytically from the logs
  and drives the staged endpoint end to end.

Verify locally with `cyberrange solve content/rooms/threat-hunt-northstar`.
