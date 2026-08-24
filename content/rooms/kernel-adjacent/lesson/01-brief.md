# Kernel Adjacent

Every serious local privilege engagement starts the same way: not
with an exploit, but with a question. What exactly is running here,
and which published bugs actually apply to that answer? Vulnerable
machine ranges in the classic style, from old boot2root images to
modern community boxes, keep proving the same lesson year after year.
Learners who fire random public exploits at a host learn almost
nothing and often break the box. Learners who read the platform
first walk away with a repeatable method. This room exists to drill
that method under conditions where honesty is enforced by machinery.

## What you will practice

First, source discipline. The container you log into reports one
kernel through ambient tools and a completely different simulated one
through the lab's sysinfo tool. That mismatch is intentional. Real
hardened hosts virtualize, sandbox, and patch in ways that make
surface output unreliable, so professionals anchor on authoritative
sources: package manifests, kernel configs, vendor advisories. You
will record the authoritative kernel string into a recon file, which
mirrors the note-taking habit that separates organized operators from
tourists.

Second, precondition analysis against real structure. The candidates
file lists three famous bugs with machine-readable bounds. One fails
on version range alone, one fails because a privileged helper binary
is simply absent, and one survives because every stated condition
holds on this platform. Notice how different those failure modes are.
Version bounds, binary presence, and feature availability are three
different kinds of evidence, and mature triage weighs each kind on
its own terms instead of pattern matching on CVE numbers alone.

Third, provable work product. The lab checker validates three gates:
your recon file must match the recorded kernel string, your chosen
candidate must be the single one whose preconditions hold, and your
preconditions file must transcribe every observed fact correctly.
Only then does it print the flag from its root-only copy. Nothing in
this room executes an exploit or touches a real kernel; the entire
exercise is the reasoning layer, graded mechanically. That is the
same reasoning layer a reviewer would audit in a real engagement
report, which is why the checker is strict about exact values.

## Scope

Only your own lab instance is in scope: SSH on port 22 of the target.
The sole privileged path is a passwordless sudo grant limited to one
checker script inside this container, which compares text files and
prints the flag without executing anything else. No exploit code,
network payloads, or system state changes exist anywhere in the
image, and nothing you type can affect anything beyond your own
session. The sudo grant is deliberately narrower than the ones you
met on earlier boxes precisely so the checker remains a grading tool
rather than part of the puzzle.

Work as if a reviewer will read your trail, because in a sense one
will. The recon file, the candidates analysis, and the preconditions
file together form exactly the evidence chain a real engagement
report needs before anyone accepts a vulnerability claim. When you
finish, the flag is the proof of completion, but the durable skill is
the triage trail you left behind: authoritative facts captured at
source, candidate reasoning written down before conclusions, and
precondition claims that match observed reality key by key. Learners
who can produce that trail on demand will find every later privilege
escalation exercise faster, because the method transfers unchanged
from simulated kernels to real fleet inventories.
