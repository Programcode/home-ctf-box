# license-to-learn

A debugger is the closest thing reversing has to a microscope, and this
room teaches its most fundamental maneuver: stopping a program at a
chosen instant and reading memory while everything is still live. The
target is an activation binary whose expected code comes out of a slow
naive loop. The loop exists precisely so that neither strings output
nor casual guessing reveals the answer; the value only ever exists in
memory at runtime, which makes it a perfect subject for a breakpoint.

## Why breakpoints beat brute force

You could try to reverse the arithmetic of the loop on paper, but that
is fragile, slow, and misses the point. The program itself computes the
answer it wants; it just never prints it. A debugger lets you borrow
the program's own work: stop execution at the exact moment validation
begins and the finished expectation sits in a global variable, ready to
read. This pattern appears everywhere in practice, from license checks
to protocol state machines. Any time a program compares your input
against something it computed, the something is already in memory, and
a breakpoint turns a secret into an observation.

## Using the provided template

The image ships /opt/challenges/cheatsheet.gdb, a working gdb script
with three blanks: where to break, what throwaway argument to run with,
and which global variable to inspect. Fill them using nm output from a
copy of the binary. The copy matters for an honest reason: debugging a
setuid executable is awkward because the kernel strips privilege gains
from traced processes, so professionals analyze plain copies and run
the privileged original only when they need its real behavior. Batch
mode keeps the whole flow scriptable, which is exactly how automated
analysis pipelines use gdb.

## Reading memory and feeding it back

The completed script breaks at report, runs with any throwaway number,
and dumps four bytes at the expectation global with x/1wx. Convert the
printed hex dword to decimal, pass it as the argument to the original
/opt/challenges/activator, and the comparison succeeds on its own
terms. No patching, no tampering: the program validates your input
honestly and rewards you with the flag. Internalize this loop of
symbol lookup, breakpoint placement, memory inspection, and replay;
it is the daily routine of anyone who debugs software they did not
write.
