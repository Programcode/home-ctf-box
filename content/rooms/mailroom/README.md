# mailroom

Medium challenge room. Enumerate mailboxes through a simulated SMTP
VRFY endpoint, then reuse a leaked temporary password to read the one
inbox that holds the flag. Points: 225.

- `room.yaml` declares objectives, scope, safety, target, tasks.
- `lesson/` holds the learner-facing brief.
- `target/` builds the Flask portal: admin status page on /, VRFY
  compatibility lookup at /api/vrfy, and basic-auth inboxes under
  /inbox/<name>. No SMTP daemon exists; the app labels itself as a
  simulation everywhere.
- `solver/solver.py` proves the intended path end to end: read the
  leak from the status page, enumerate candidates through /api/vrfy,
  walk the confirmed inboxes with basic auth.

Verify locally with `cyberrange solve content/rooms/mailroom`.
