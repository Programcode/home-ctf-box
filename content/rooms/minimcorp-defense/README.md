# minimcorp-defense

Hard investigation room, single task worth 400 points. One locked Flask
container plays the MinimCorp incident response console: it serves four
synthetic evidence exports (edge access log, wiki audit, finance API access,
directory-sim verification log) frozen from the same three-host estate the
red-team room simulates, plus a small stateful case API. There is no SIEM
backend and no network; everything is one process that resets on restart.

Workflow: read /case and /playbook, fetch the exports from /evidence, submit
/timeline (four ordered stage slugs with minute-precision first-event times),
/accounts (identities authenticated as, impersonated, or whose records were
returned), and /contain (five actions covering every root cause, nothing
destructive, nothing overbroad). POST /close-case returns the flag only when
all three stages are accepted.

- `room.yaml` declares objectives, scope, safety, target, tasks.
- `lesson/` holds the learner-facing brief.
- `target/app.py` serves evidence and grades the three case stages.
- `solver/solver.py` parses every answer out of the evidence exports with
  httpx instead of hardcoding them.

Single-container disclosure appears prominently in the safety
reviewer notes, the landing page, the README, and the lesson.

Verify locally with `cyberrange solve content/rooms/minimcorp-defense`.
