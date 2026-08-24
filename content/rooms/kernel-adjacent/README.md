# Kernel Adjacent

Medium box room. A version-triage box where the lab checker validates
recon, candidate selection, and precondition edits before printing the
flag. No real exploits run anywhere; the exercise is the triage
method itself. Points: 300.

- `room.yaml` declares objectives, scope, safety, target, tasks.
- `lesson/` holds the learner-facing brief.
- `target/` builds the Debian box: sshd on 22, a simulated sysinfo
  facts tool, three documented CVE candidates with machine-readable
  preconditions, and a sudo-granted exploit-checker that verifies all
  three gates before revealing the flag.
- `solver/solver.py` proves the intended path end to end: it parses
  the facts and candidates, derives the single applicable candidate,
  writes the recon and preconditions files, then runs the checker.

Verify locally with `cyberrange solve content/rooms/kernel-adjacent`.
