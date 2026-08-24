# Detection Forge

Hard challenge detection-engineering room. Author four regex rules
against labeled attack traces and pass every positive and negative
fixture on the forge validator. Points: 300.

- `room.yaml` declares objectives, scope, safety, target, tasks.
- `lesson/` holds the learner-facing brief.
- `target/` builds the forge and fixture validator (Flask, port 8000).
- `solver/solver.py` ships a tuned ruleset and proves it validates.

Verify locally with `cyberrange solve content/rooms/detection-forge`.
