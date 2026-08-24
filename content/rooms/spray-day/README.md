# spray-day

Easy challenge web lab for password-spraying concepts, honestly
simulated. A fictional staff portal locks accounts after 3 failed
sign-ins (90 second lockout), publishes a directory of 11 addresses of
which 7 are real mailboxes, and leaks the difference through its reset
form. The one seasonal password assembles from two artifacts: the
policy page (scheme plus theme word Riverbank) and the facilities memo
(mascot Otter, building number 07). Spraying RiverbankOtter07 across
confirmed mailboxes, one attempt each, opens a session that shows the
flag. Points: 150.

- `room.yaml` declares objectives, scope, safety, locked target, tasks.
- `lesson/` teaches why spraying defeats per-account lockout counters
  and which defenses actually blunt it.
- `target/` builds a python:3.12-alpine Flask app (port 8000, locked
  profile) with policy, directory, memo, reset oracle, and login.
- `solver/solver.py` proves the intended path with httpx: enumerate via
  /forgot, assemble the password from both pages, spray one attempt per
  account.

Verify locally with `cyberrange solve content/rooms/spray-day`.
