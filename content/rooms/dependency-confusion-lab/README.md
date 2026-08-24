# Dependency Confusion Lab

Medium challenge supply-chain room. Squat an unclaimed internal package
name on a simulated mixed-feed registry using a maintainer token recovered
from an archived CI artifact. Points: 250.

- `room.yaml` declares objectives, scope, safety, target, tasks.
- `lesson/` holds the learner-facing brief.
- `target/` builds the registry lab (Flask, port 8000).
- `solver/solver.py` proves the full takeover path: registry recon,
  token recovery, publish claim, canary confirmation.

Verify locally with `cyberrange solve content/rooms/dependency-confusion-lab`.
