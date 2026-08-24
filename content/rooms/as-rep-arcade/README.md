# as-rep-arcade

Medium challenge Windows room. Accounts with Kerberos pre-auth
disabled let anyone request their AS-REP encrypted material; a Flask
KDC sim issues XOR-SIM enc-parts over a documented 16-byte preamble,
the published wordlist cracks one account, and POST /redeem trades the
credential for the flag. Points: 225.

- `room.yaml` declares objectives, scope, safety, target, tasks.
- `lesson/` holds the learner-facing brief.
- `target/` builds the Flask fake KDC (port 8000, /tools clients).
- `solver/solver.py` proves the intended path end to end with httpx.

Verify locally with `cyberrange solve content/rooms/as-rep-arcade`.
