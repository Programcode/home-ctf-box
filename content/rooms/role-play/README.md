# role-play

Medium challenge room for the defense-cloud track. A simulated IAM
plane signs the learner in as dev-cli, whose policy allows invoking
one function (nightly-report) and passing one role (report-runner),
with direct assumption denied. The intended chain runs two hops:
invoke with pass_role to enter report-runner, read its policy, then
invoke admin-console passing admin-role. The resulting context token
unlocks GET /admin/context and the flag. Points: 250.

- `room.yaml` declares objectives, scope, locked profile, one task
  with tiered hints.
- `lesson/` explains PassRole plus InvokeFunction composition and
  discloses every simulation seam.
- `target/` builds a Flask JSON API on port 8000 with readable policy
  documents and deterministic sha256 context tokens.
- `solver/solver.py` derives both hops from the policy documents via
  httpx rather than hardcoded names.

Verify locally with `cyberrange solve content/rooms/role-play`.
