# license-to-learn

Easy challenge reversing room. The activator at
`/opt/challenges/activator` computes its expected numeric code through
a slow naive loop and compares your argument against it. There are no
ptrace games: the honest path is a debugger. Learners complete the
fill-in-the-blanks gdb template at `/opt/challenges/cheatsheet.gdb`,
break at the comparison point on a plain copy of the binary, dump the
computed expectation from memory, then feed it back to the real setuid
binary to collect the flag.

- `room.yaml` declares objectives, scope, safety, target, tasks.
- `lesson/` holds the learner-facing brief.
- `target/` builds the Debian SSH box (port 22, learner/learner) with
  gdb installed and the cheatsheet template staged in /opt/challenges.
- `solver/solver.py` proves the intended path end to end with paramiko:
  nm discovery, template completion, batch gdb memory read, feedback run.

Verify locally with `cyberrange solve content/rooms/license-to-learn`.
