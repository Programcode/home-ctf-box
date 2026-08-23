# route-less-traveled

Medium challenge room. Metrics endpoint leaks a simulated interface
table; routing to the tunnel subnet returns the remote segment page.
Points: 225.

- `room.yaml` declares objectives, scope, safety, target, tasks.
- `lesson/` holds the learner-facing brief.
- `target/` builds the gateway simulator (Flask on 8000 with /metrics
  and POST /route).
- `solver/solver.py` proves the intended path end to end: parse
  metrics lines, route to the tunsim0 subnet first.

Verify locally with `cyberrange solve content/rooms/route-less-traveled`.
