# graph-the-domain

Easy challenge Windows-track room, honestly Linux-hosted. A locked
Flask app serves a fictional BloodHound-style collector graph at
/collect/graph.json (users, groups, computers; MemberOf,
CanResetPassword, HasSession, AdminOn edges) and quizzes five derived
answers at /quiz. The full correct answer set unlocks the per-session
flag; the room validator is per_session_flag with the exact/set check
folded into the single quiz flow. Points: 200.

- `room.yaml` declares objectives, scope, safety, locked target, tasks.
- `lesson/` teaches graph thinking for attack paths and discloses the
  fictional data.
- `target/` builds a python:3.12-alpine Flask app (port 8000, locked
  profile) serving the collector JSON and the quiz endpoint.
- `solver/solver.py` proves the intended path with httpx plus stdlib:
  fetch the graph, BFS the shortest path, scan edges for the rest,
  submit the complete set.

Verify locally with `cyberrange solve content/rooms/graph-the-domain`.
