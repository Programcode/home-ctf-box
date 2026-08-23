# service-please

Medium challenge Linux room. A root-run supervisor loop sources
/etc/app/env every thirty seconds and that file is world writable;
learners append copy commands to the config and collect the flag after
the next cycle. Points: 225.

- `room.yaml` declares objectives, scope, safety, target, tasks.
- `lesson/` holds the learner-facing brief.
- `target/` builds the Debian SSH box (port 22, learner/learner).
- `solver/solver.py` proves the intended path end to end with paramiko.

Verify locally with `cyberrange solve content/rooms/service-please`.
