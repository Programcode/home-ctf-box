# capable-enough

Easy challenge Linux room. The stock Python interpreter carries
cap_setuid=ep, a capability no stock Debian binary should have; learners
find it with getcap and use it to read /root/flag.txt as root. Points: 200.

- `room.yaml` declares objectives, scope, safety, target, tasks.
- `lesson/` holds the learner-facing brief.
- `target/` builds the Debian SSH box (port 22, learner/learner).
- `solver/solver.py` proves the intended path end to end with paramiko.

Verify locally with `cyberrange solve content/rooms/capable-enough`.
