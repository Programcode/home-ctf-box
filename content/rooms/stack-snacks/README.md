# stack-snacks

Medium challenge binary fundamentals room. The snack CLI reads far past
its 64-byte buffer but ships with canary, NX, and PIE enabled, so a
classic overflow exploit is impossible by design; learners prove where
the guard sits with pattern inputs of increasing length instead. The
snack-vendor kiosk service (port 9994) carries an adjacent format-string
bug in its order command; leaking its stack canary plus answering the
guided quiz (canary value and byte offset) pays out the flag.

- `room.yaml` declares objectives, scope, safety, target, tasks.
- `lesson/` holds the learner-facing brief.
- `target/` builds the Debian SSH box (port 22, learner/learner); the
  kiosk supervisor runs from the entrypoint and pins the flag file open
  before dropping to uid 1000.
- `solver/solver.py` proves the intended path end to end with paramiko:
  boundary demonstration, positional %p leak walk, candidate filtering,
  quiz answers.

Verify locally with `cyberrange solve content/rooms/stack-snacks`.
