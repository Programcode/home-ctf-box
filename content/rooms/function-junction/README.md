# function-junction

Medium challenge room for the defense-cloud track. A simulated
function platform hosts two handlers: thumbnailer requires signed
storage events, while webhook-relay accepts unauthenticated HTTP
invokes, forwards JSON to a caller-chosen destination_url, and carries
a documented debug mode attaching the process environment summary to
deliveries. Learners aim an invoke at the provided /sink collector
(simulating their own internet receiver), read the leaked
SECRETS_BLOB out of /sink/events, and submit the flag inside.
Points: 225.

- `room.yaml` declares objectives, scope, locked profile, one task
  with tiered hints.
- `lesson/` walks the misconfiguration pair and discloses the sink
  stand-in explicitly.
- `target/` builds the Flask platform on port 8000; deliveries are
  local urllib posts, no egress.
- `solver/solver.py` invokes with debug_hook enabled and extracts the
  flag from the collected sink events via httpx.

Verify locally with `cyberrange solve content/rooms/function-junction`.
