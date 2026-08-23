# capable-enough

Capabilities are how modern Linux splits the all-or-nothing power of
root into individual grants. They also fail in interesting ways when an
operator pastes a remediation command without understanding it. This box
carries one such leftover, and your job is to notice it, name it, and
turn it into root.

## What you will practice

- Sweeping a filesystem for file capabilities with getcap and reading
  the output with the same care you give ls -l.
- Reasoning about cap_setuid on an interpreter rather than on a
  purpose-built helper.
- Using Python's os module to change your own user ID once the
  capability says you may.

## The scenario

A deployment guide once suggested giving a build tool permission to
switch users. The command that landed on this box granted
cap_setuid=ep to /usr/bin/python3.11 instead of the tool it was meant
for. Nothing else on the filesystem carries capabilities, so a full
sweep makes the mistake impossible to miss.

## How to work it

Start from enumeration, not from memory. Run the capability sweep,
confirm the owning user, and ask what the effective set actually
permits before you run anything. When you escalate, read exactly one
file: /root/flag.txt contains the FLAG value for submission.

## Scope

Only the box at `ssh://target:22` is in scope. Nothing outside your lab
instance is a target. Log in as learner with password learner.
