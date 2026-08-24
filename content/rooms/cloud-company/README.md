# cloud-company

Insane range capstone, single task worth 500 points. One locked Flask
container simulates a local-cloud estate: iam.cloudcompany.internal,
s3.cloudcompany.internal, functions.cloudcompany.internal, and
audit.cloudcompany.internal run as separate APIs on loopback ports
9101-9104 behind a front controller on port 8000 that routes by Host header.
Five stages yield five four-character fragments of the session flag;
/board verifies all five and returns the assembled master flag, the only
graded value. Sub-flag fragments are intermediate state and documented as
such in the task solution.

Stage chain: bootstrap developer key, assume-role graph privesc dev-onboard
to ci-runner to deploy-bot to ops-admin (fragment 1), anonymous bucket
listing into an ops-gated confidential archive object (fragment 2),
backdoor identification on image-resizer revision 7 plus verdict POST
(fragment 3), hash-chain gap analysis over audit entries plus deletion
verdict (fragment 4), and exfil destination verdict from quarantine records
(fragment 5).

- `room.yaml` declares objectives, scope, safety, target, tasks.
- `lesson/` holds the learner-facing brief.
- `target/app.py` builds all four service backends, the proxy controller,
  and the fragment board.
- `solver/solver.py` walks every stage with httpx, recomputes the hash
  chain itself, and derives each fragment without hardcoding.

Single-container disclosure appears prominently in the safety
reviewer notes, the landing page, the README, and the lesson.

Verify locally with `cyberrange solve content/rooms/cloud-company`.
