# full-spectrum

Insane range capstone worth 600 points across two graded deliverables.
One locked Flask container plays five hosts behind a Host-header front
controller: portal.spectrum.io, git.internal.spectrum.io,
core-db.spectrum.internal, archive.spectrum.internal, and ir.spectrum.io.

Red chain (task red-chain, 300 points): reused partner credentials from the
portal's own exposure-check corpus give initial access; single sign-on
pivots the session header into internal git; CI config leaks a shared
console key; core-db session impersonation yields an admin sid and staging
dataset; archive staging pays the first flag. Blue deliverable (task
blue-report, 300 points): ir.spectrum.io grades scope in attack order, four
findings with severity mappings, and ordered remediation priorities via
/review, refusing reports until the red chain is complete. Only full red
plus blue completion yields the second flag.

- `room.yaml` declares objectives, scope, safety, target, both tasks.
- `lesson/` holds the learner-facing brief.
- `target/app.py` builds all five host backends plus the proxy controller
  and the server-side kill-chain state machine.
- `solver/solver.py` runs the whole chain and files a rubric-perfect report
  with httpx, deriving every token without hardcoding.

Single-container disclosure appears prominently in the safety reviewer
notes, the landing page, the README, and the lesson.

Verify locally with `cyberrange solve content/rooms/full-spectrum`.
