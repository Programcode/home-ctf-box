# idor-invoices

Beginner guided web room. Insecure direct object reference: invoice URLs
load any record with no ownership check, and another customer's bill
prints an internal release code. Points: 125.

- `room.yaml` declares objectives, scope, safety, target, tasks.
- `lesson/` holds the learner-facing brief.
- `target/` builds the vulnerable service (Flask, port 8000).
- `solver/solver.py` proves the intended path end to end.

Verify locally with `cyberrange solve content/rooms/idor-invoices`.
