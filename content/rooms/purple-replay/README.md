# purple-replay

Hard purple-team range, single task worth 350 points. One locked Flask
container plays both sides: the victim web app lives under /victim/ and the
purple lab control plane under /lab/, in the same process. You replay a
provided four-stage attack script (recon, brute-force, exploit, exfil)
against the victim routes with the border-stamped attacker address, then
author one detection rule per stage and submit it to a gate that validates
it against that stage's attacker events and the fixed benign traffic pool.
A rule that fires on benign noise fails immediately. Clearing all four
gates and passing the finalize re-check returns the flag.

Rule DSL: {"match": [{"field": ..., "op": "equals|contains|startswith|>=",
"value": ...}], "at_least": N}; conditions are ANDed; fields come from the
event record (src_ip, method, target, status, bytes_in).

- `room.yaml` declares objectives, scope, safety, target, tasks.
- `lesson/` holds the learner-facing brief.
- `target/app.py` hosts victim routes, the deterministic benign pool, and
  the stage-gate evaluator.
- `solver/solver.py` replays every scripted step and derives each rule from
  the stage metadata instead of hardcoding captured flags.

Single-container disclosure appears prominently in the safety
reviewer notes, the landing page, the README, and the lesson.

Verify locally with `cyberrange solve content/rooms/purple-replay`.
