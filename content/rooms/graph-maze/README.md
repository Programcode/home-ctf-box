# graph-maze

Medium challenge web room. GraphQL gateway with introspection enabled,
batching accepted, and no object-level authorization on note nodes.
Points: 225.

- `room.yaml` declares objectives, scope, safety, target, tasks.
- `lesson/` holds the learner-facing brief.
- `target/` builds the vulnerable service (Flask, port 8000).
- `solver/solver.py` proves the intended path end to end.

Verify locally with `cyberrange solve content/rooms/graph-maze`.
