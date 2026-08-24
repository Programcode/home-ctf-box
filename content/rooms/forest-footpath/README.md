# forest-footpath

Hard challenge Windows-AD room. Two simulated domains (child.corp,
parent.corp) run as JSON APIs on loopback ports behind one front
controller on port 8000 that routes by Host header. Learners read
/trusts on the child, authenticate as learner/learner, chain the child
token through the parent's /trust-exchange, then fetch the flag from
/enterprise/path. Points: 300.

- `room.yaml` declares objectives, scope, safety, target, tasks.
- `lesson/` holds the learner-facing brief.
- `target/` builds the locked Flask container (port 8000 only).
- `solver/solver.py` proves the token chain end to end with httpx.

Single-container disclosure: both domains are simulated inside one
box; nothing here contacts real Active Directory.

Verify locally with `cyberrange solve content/rooms/forest-footpath`.
