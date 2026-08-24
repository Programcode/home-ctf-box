# Intentional Leak

Medium challenge room for Android-style component attacks. A simulated
intent router exposes an activity stack with an exported debug
renderer whose extras reach a privileged template context, chaining
into a settings leak and an internal-endpoint bypass. Points: 225.

- `room.yaml` declares objectives, scope, safety, target, tasks.
- `lesson/` maps the chain to exported components, bridges, and logging.
- `target/` builds the debug stack (Flask, port 8000).
- `solver/solver.py` proves enumeration to intent craft to leak end to end.

No device or emulator exists anywhere; the whole app is data structures
in one Flask container. Verify locally with
`cyberrange solve content/rooms/intentional-leak`.
