# container-window

Medium challenge Linux room. The box is itself a container and says so;
no docker socket exists, and the host relationship is modeled by a
sudo-wrapped read-only introspection tool over /hostsim, where
/hostsim/root/flag.txt hides behind mode 600. Points: 250.

- `room.yaml` declares objectives, scope, safety, target, tasks.
- `lesson/` holds the learner-facing brief.
- `target/` builds the Debian SSH box (port 22, learner/learner).
- `solver/solver.py` proves the intended path end to end with paramiko.

Verify locally with `cyberrange solve content/rooms/container-window`.
