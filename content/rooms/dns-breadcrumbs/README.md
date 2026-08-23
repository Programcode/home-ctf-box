# dns-breadcrumbs

Easy challenge room. Authoritative DNS for lab.internal with A record
hints, a TXT flag, and an open zone transfer. Points: 175.

- `room.yaml` declares objectives, scope, safety, target, tasks.
- `lesson/` holds the learner-facing brief.
- `target/` builds the name server (dnslib on UDP/TCP 53 plus a Flask
  reception page on 8000). Runs unprivileged uid 10001; the elevated
  profile exists only to grant CAP_NET_BIND_SERVICE for port 53.
- `solver/solver.py` proves the intended path end to end with a
  minimal struct-only DNS client from the attacker image.

Verify locally with `cyberrange solve content/rooms/dns-breadcrumbs`.
