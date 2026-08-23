# Kernel of Truth

Version analysis is the least glamorous part of offensive security
and the part professionals get paid for. Anyone can run an exploit
script; knowing which of forty CVEs actually applies to the box in
front of you is the skill. This room gives you a legacy appliance
slice that reports its kernel through a small HTTP endpoint, three
candidate vulnerabilities, and research notes that record why two of
them cannot work here. Your task is to perform the elimination honestly
and only then touch the simulator.

## What you will practice

- Trusting authoritative version sources over convenient ones. Inside
  a container, `uname` prints the host's kernel, which is useless for
  judging the appliance. The room's sysinfo API at
  `http://target:8000/api/sysinfo` reports kernel 5.4.0-42-generic and
  explicitly labels itself as the simulated authority. Knowing when a
  version string is real, fake, or simply irrelevant is half the job.
- Reading preconditions like an analyst. The notes beside the
  simulator list each candidate with a verdict and its reasoning:
  CVE-2022-0847 needs pipe code introduced in 5.8, so this 5.4 build
  predates the bug; CVE-2021-4034 needs a setuid pkexec binary that
  policykit would normally install, and this image ships without it;
  CVE-2021-3490 matches both the affected range and the recorded eBPF
  conditions. One survives. Your write-up should be able to say why,
  in those words or better.
- Driving a tool only after understanding it. The simulator at
  `/usr/local/bin/exploit-sim` validates every recorded condition
  before printing anything, and it refuses wrong candidates with their
  failure reasons. It contains no exploit code; it is the grading
  oracle for your deduction.

## An honest note about simulation

No kernel memory corruption happens in this room, because making a
container emulate vulnerable kernel internals reliably is neither
honest nor useful. The simulator stands in for the exploit step the
way a flight simulator stands in for a runway: the decision-making
before launch is fully real, the mechanics are represented. When you
move to dedicated binary exploitation rooms later in the curriculum,
the version triage you practiced here will already feel routine.

## Scope

In scope are `ssh://target:22` as learner and
`http://target:8000/api/sysinfo`, both inside this lab container.
Nothing here touches your host kernel, and no payload leaves the lab
network. Treat every CVE identifier as fictional exam material unless
you have verified applicability against a real asset inventory.
