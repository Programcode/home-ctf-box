# strings-attached

Beginner challenge reversing room. A small bookkeeping binary at
`/opt/challenges/ledger` advertises two harmless options in its usage
line while a third, `--export-secrets`, hides in the compiled string
table. Learners triage with `file` and `strings`, run the hidden mode,
and undo the single-byte XOR it applies before printing.

- `room.yaml` declares objectives, scope, safety, target, tasks.
- `lesson/` holds the learner-facing brief.
- `target/` builds the Debian SSH box (port 22, learner/learner).
- `solver/solver.py` proves the intended path end to end with paramiko:
  strings discovery, export capture, XOR decode against the per-session
  flag derivation.

Verify locally with `cyberrange solve content/rooms/strings-attached`.
