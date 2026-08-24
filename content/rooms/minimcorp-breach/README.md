# minimcorp-breach

Hard range capstone, single task worth 400 points. One locked Flask
container simulates a three-host MinimCorp estate: vpn-edge.minimcorp.net,
wiki.corp.minimcorp.net, and finance.minimcorp.net run as separate APIs on
loopback ports 9101-9103 behind a front controller on port 8000 that routes
by Host header. Each host guards a four-character fragment of the session
flag; /scoreboard verifies all three plus a forged directory-sim admin
token and returns the assembled master flag, which is the only graded value.
Sub-flag fragments are intermediate state and documented as such in the task
solution.

Kill chain: vpn-edge stale rollback config leak, base64 encoded (creds +
fragment 1), wiki basic-auth recon with the fragment hidden in revision
metadata and the runbook handing over the finance key and signing scheme
(fragment 2), finance API IDOR over sequential employee ids (fragment 3),
then md5 token forgery against the directory sim using the unrotated legacy
secret.

- `room.yaml` declares objectives, scope, safety, target, tasks.
- `lesson/` holds the learner-facing brief.
- `target/app.py` builds all three backends plus the proxy controller.
- `solver/solver.py` walks the full chain with httpx, deriving every
  fragment and the forged token without hardcoding.

Single-container disclosure appears prominently in the safety
reviewer notes, the landing page, the README, and the lesson.

Verify locally with `cyberrange solve content/rooms/minimcorp-breach`.
