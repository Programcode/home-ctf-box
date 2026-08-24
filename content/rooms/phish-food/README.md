# Phish Food

Beginner challenge SOC room. Raw .eml header analysis against a Flask
case page: spoofed From, mismatched Return-Path, lookalike link domain,
answered through an indicator quiz. Points: 125.

- `room.yaml` declares objectives, scope, safety, target, tasks.
- `lesson/` holds the learner-facing brief.
- `target/` builds the case service (Flask, port 8000) serving the
  preserved message and the indicator quiz.
- `solver/solver.py` proves the intended parsing path end to end using
  only the Python standard library email module plus httpx.

Verify locally with `cyberrange solve content/rooms/phish-food`.
