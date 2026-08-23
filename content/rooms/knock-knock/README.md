# knock-knock

Beginner challenge room. UDP port knocking against a Flask vault that
only opens for a valid three-port sequence. Points: 150.

- `room.yaml` declares objectives, scope, safety, target, tasks.
- `lesson/` holds the learner-facing brief.
- `target/` builds the gated vault (Flask HTTP on 8000 plus UDP
  daemons on 7000, 8000, 9000, and the status probe on 9999).
- `solver/solver.py` proves the intended path end to end with raw
  sockets from the attacker image.

Verify locally with `cyberrange solve content/rooms/knock-knock`.
