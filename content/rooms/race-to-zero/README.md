# race-to-zero

Hard challenge web room. Withdrawal race condition: the fraud scorer
reads the balance, sleeps, then writes, so concurrent requests both
clear the check and drive the account negative. Points: 250.

- `room.yaml` declares objectives, scope, safety, target, tasks.
- `lesson/` holds the learner-facing brief.
- `target/` builds the vulnerable service (Flask, port 8000).
- `solver/solver.py` proves the intended path end to end.

Verify locally with `cyberrange solve content/rooms/race-to-zero`.
