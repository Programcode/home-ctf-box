# certificate-misprint

Hard challenge Windows room. A Flask CA-SIM issues toy-RSA signed
cert-tokens after a template check; one template accepts a
requester-supplied SAN, so the low-privilege lab user enrolls with
SAN=administrator and opens /admin for the flag. Points: 275.

- `room.yaml` declares objectives, scope, safety, target, tasks.
- `lesson/` holds the learner-facing brief.
- `target/` builds the Flask fake CA (port 8000).
- `solver/solver.py` proves the intended path end to end with httpx.

Verify locally with `cyberrange solve content/rooms/certificate-misprint`.
