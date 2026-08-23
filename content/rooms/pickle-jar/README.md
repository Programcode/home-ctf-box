# pickle-jar

Medium challenge web room. Unsafe deserialization through
pickle.loads on client-controlled session state. Points: 275.

- `room.yaml` declares objectives, scope, safety, target, tasks.
- `lesson/` holds the learner-facing brief.
- `target/` builds the vulnerable service (Flask, port 8000) and writes
  the flag to `/flag.txt` at startup so the payload has something to read.
- `solver/solver.py` proves the intended path end to end.

Verify locally with `cyberrange solve content/rooms/pickle-jar`.
