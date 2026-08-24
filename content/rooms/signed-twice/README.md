# signed-twice

Hard challenge crypto room. DSA nonce reuse broken into full private
key recovery and token forgery against a stdlib-Python Flask signer.
Points: 275.

- `room.yaml` declares objectives, scope, safety, target, tasks.
- `lesson/` holds the learner-facing brief.
- `target/` builds the audit signer (Flask, port 8000).
- `solver/solver.py` proves the k-reuse path end to end with integer math.

Verify locally with `cyberrange solve content/rooms/signed-twice`.
