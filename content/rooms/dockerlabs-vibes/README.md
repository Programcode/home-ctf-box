# Dockerlabs Vibes

Easy box room. The docker-group misconfiguration concept, simulated
honestly: a dockersim helper with a documented API stands in for the
daemon, and its mount-and-run equivalent reads a root-only flag.
Points: 225.

- `room.yaml` declares objectives, scope, safety, target, tasks. The
  safety notes disclose plainly that no real Docker exists here.
- `lesson/` holds the learner-facing brief.
- `target/` builds the Debian box: sshd on 22, learner in the docker
  group, a sudo grant limited to dockersim for group members, and a
  /hostsim tree whose root-only flag file plays the protected host
  path.
- `solver/solver.py` proves the intended path end to end: group
  check, manual read, HOSTSYNC discovery, denied direct cat, then the
  documented daemon-sim run.

Verify locally with `cyberrange solve content/rooms/dockerlabs-vibes`.
