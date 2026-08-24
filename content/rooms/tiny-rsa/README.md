# tiny-rsa

Medium challenge crypto room. Textbook RSA with 512-bit modulus and
e=3 broken by integer cube roots against a Flask sealing desk. Points: 200.

- `room.yaml` declares objectives, scope, safety, target, tasks.
- `lesson/` holds the learner-facing brief.
- `target/` builds the sealing service (Flask, port 8000).
- `solver/solver.py` proves the cube-root path with pure integer math.

Verify locally with `cyberrange solve content/rooms/tiny-rsa`.
