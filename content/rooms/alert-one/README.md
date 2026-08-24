# Alert One

Beginner guided SOC room. Eight synthetic SIEM alerts with enrichment
fields, triaged through a documented two-question rule against a Flask
training desk. Points: 100.

- `room.yaml` declares objectives, scope, safety, target, tasks.
- `lesson/` holds the learner-facing brief.
- `target/` builds the SOC desk service (Flask, port 8000) with the
  fixed alert queue and the classification endpoint.
- `solver/solver.py` proves the intended triage path end to end.

Verify locally with `cyberrange solve content/rooms/alert-one`.
