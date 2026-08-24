# relay-station

Hard challenge Windows room. A Flask lab stages a simulated NTLM
relay without any NTLM: deterministic per-target challenges, a printer
device that answers whatever it is handed, and a fileserver endpoint
that accepts proofs minted for its own challenge. The provided
relay-sim client chains capture, coercion, and relay for the flag.
Points: 300.

- `room.yaml` declares objectives, scope, safety, target, tasks.
- `lesson/` holds the learner-facing brief.
- `target/` builds the Flask relay stage (port 8000).
- `solver/solver.py` proves the intended path end to end with httpx.

Verify locally with `cyberrange solve content/rooms/relay-station`.
