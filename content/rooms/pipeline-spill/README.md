# Pipeline Spill

Easy challenge supply-chain room. A CI build log masks a deploy token in
two different ways, and each mask covers only half. Points: 150.

- `room.yaml` declares objectives, scope, safety, target, tasks.
- `lesson/` holds the learner-facing brief.
- `target/` builds the case page and deploy endpoint (Flask, port 8000).
- `solver/solver.py` proves the two-line reconstruction path end to end.

Verify locally with `cyberrange solve content/rooms/pipeline-spill`.
