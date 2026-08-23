# namespace-escape-plan

Hard challenge room. Sessions start inside a chroot sandbox at /jail
courtesy of an SUID helper whose administrative subcommand forgets to
chdir("/") after chroot(). Stage a toolkit, run the classic
double-chroot escape, and read the real flag on the true root.
Points: 300.

- `room.yaml` declares objectives, scope, safety, target, tasks.
- `lesson/` holds the learner-facing brief.
- `target/` builds the Debian box: sshd on 22 (learner/learner) whose
  login shell is the static SUID-root jailctl helper, a populated
  /jail (busybox applets, device nodes, decoy flag), and the real
  flag at /flag.txt outside the jail.
- `solver/solver.py` proves the intended path end to end over
  paramiko: read the decoy, stage busybox in /tmp/esc, then perform
  both chroots with the relative-path climb through the stranded cwd.

Verify locally with `cyberrange solve content/rooms/namespace-escape-plan`.
