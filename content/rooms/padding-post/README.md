# padding-post

Medium challenge crypto room. Classic Vaudenay CBC padding oracle
against a Flask plus cryptography service that returns only a padding
boolean. Points: 250.

- `room.yaml` declares objectives, scope, safety, target, tasks.
- `lesson/` holds the learner-facing brief.
- `target/` builds the oracle service (Flask, port 8000).
- `solver/solver.py` implements the byte-at-a-time attack with stdlib
  integers only (no crypto libraries attacker-side).

Verify locally with `cyberrange solve content/rooms/padding-post`.

Note: `/api/decrypt` is intentionally not rate limited so the adaptive
oracle exercise stays teachable; the room network is isolated and the
service holds synthetic data only.
