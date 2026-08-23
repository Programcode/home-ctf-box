# fetch-boy

Easy challenge room. The Peeker preview service fetches arbitrary URLs
from the server side, and an admin service on the container's loopback
interface at port 9001 leaks its flag through the proxy. Points: 200.

- `room.yaml` declares objectives, scope, safety, target, tasks.
- `lesson/` holds the learner-facing brief.
- `target/` builds the vulnerable service (Flask, port 8000).
- `solver/solver.py` proves the intended path end to end.

Verify locally with `cyberrange solve content/rooms/fetch-boy`.
