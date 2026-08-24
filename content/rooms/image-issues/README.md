# Image Issues

Medium investigation supply-chain room. An OCI-style image manifest and
per-layer tar listings reveal a live database env file baked into the
build. Points: 225.

- `room.yaml` declares objectives, scope, safety, target, tasks.
- `lesson/` holds the learner-facing brief.
- `target/` builds the evidence case and admin db console (Flask, port 8000).
- `solver/solver.py` proves the full path: history-to-layer mapping,
  listing inspection, credential extraction, console unlock.

Verify locally with `cyberrange solve content/rooms/image-issues`.
