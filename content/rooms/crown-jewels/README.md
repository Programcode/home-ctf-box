# crown-jewels

Insane range capstone, single task worth 500 points. One locked Flask
container simulates a five-host estate: web.dmz, db.internal, filesrv,
dc01, and workstation7 run as separate APIs on loopback ports 9101-9105
behind a front controller on port 8000 that routes by Host header.
Each host guards a four-character fragment of the session flag;
/scoreboard verifies all five and returns the assembled master flag,
which is the only graded value. Sub-flag fragments are intermediate
state and documented as such in the task solution.

Kill chain: web.dmz XOR-obfuscated config leak (creds + fragment 1),
db.internal parameterization claim broken by UNION injection on
/archive (fragment 2 + intel), filesrv hidden share backup$ log
(fragment 3), dc01 as-rep-style crack via served wordlist against a
rot+7 cipher (fragment 4), workstation7 persistence artifact sweep
(fragment 5).

- `room.yaml` declares objectives, scope, safety, target, tasks.
- `lesson/` holds the learner-facing brief.
- `target/app.py` builds all five backends plus the proxy controller.
- `solver/solver.py` walks the full chain with httpx, deriving every
  fragment without hardcoding.

Single-container disclosure appears prominently in the safety
reviewer notes, the landing page, the README, and the lesson.

Verify locally with `cyberrange solve content/rooms/crown-jewels`.
