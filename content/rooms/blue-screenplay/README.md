# blue-screenplay

Medium investigation Windows-AD room. A locked Flask container serves
two evtx-sim JSON exports (Security and System channels) plus an asset
inventory under /evidence. Learners build a timeline, answer three
questions (compromised account, first failed service, lateral movement
source IP), and POST them to /report, which verifies each field and
returns the flag on a complete match. Points: 250.

- `room.yaml` declares objectives, scope, safety, target, tasks.
- `lesson/` holds the learner-facing brief.
- `target/` builds the locked container; evidence is deterministic JSON.
- `solver/solver.py` derives all three answers from the logs with httpx,
  no hardcoding.

Single-container disclosure: no Windows kernel exists here; the
channels are static JSON shaped like evtx exports.

Verify locally with `cyberrange solve content/rooms/blue-screenplay`.
