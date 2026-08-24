# delegated-trust

Medium challenge Windows room. A Flask DC-SIM publishes its delegation
configuration showing svc_web may impersonate administrator; recon
material leaks svc_web credentials, the documented /tgs flow mints a
simulated S4U token, and /dc/admin-only honors it for the flag.
Points: 250.

- `room.yaml` declares objectives, scope, safety, target, tasks.
- `lesson/` holds the learner-facing brief.
- `target/` builds the Flask fake domain controller (port 8000).
- `solver/solver.py` proves the intended path end to end with httpx.

Verify locally with `cyberrange solve content/rooms/delegated-trust`.
