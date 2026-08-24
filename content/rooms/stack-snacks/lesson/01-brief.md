# stack-snacks

The classic stack overflow story goes: fill a buffer, overwrite the
saved return address, point it somewhere useful. Modern toolchains
respond with three separate defenses, and this room exists so you can
watch each one change the attacker's math. The snack CLI binary reads
up to 256 bytes into a 64-byte buffer, but it is compiled with a stack
canary, NX, and PIE, and that combination is deliberate: full
exploitation here is impossible, and understanding why matters more
than any single trick.

## What each mitigation removes

A stack canary places a random value between local buffers and saved
control data; overwriting past the buffer disturbs it, and the program
aborts itself on return instead of following your bytes. NX marks stack
memory non-executable, so even perfect control of execution flow cannot
run shellcode you planted there. PIE randomizes the binary's own load
address, which breaks any chain built from fixed addresses. Together
they convert one elegant bug into three separate research problems, and
that conversion is exactly why real attackers pivot to logic bugs and
information leaks instead. This room gives you a sanctioned leak in the
form of a format-string bug next door.

## Measuring the guard empirically

You do not need a debugger to locate the canary boundary. Feed the
snack binary a 56-byte pattern: it exits cleanly because everything fit.
Feed it 96 bytes: the process dies with the stack smashing detector's
message. Somewhere between those lengths your bytes first touched the
guard, and with a couple more probes you can pin the offset exactly.
This habit, bisecting crash boundaries with generated patterns, is how
professionals map an unfamiliar binary's frame layout quickly and
safely, and it works identically on any architecture or toolchain.

## Leaking the canary honestly

The snack-vendor kiosk on port 9994 passes order text straight to
fprintf as its format string. Positional verbs such as %7$p read values
out of the running stack frame and print them back, and among those
values sits the kiosk's live guard value. Canaries always end in a zero
byte, which makes them stand out from pointers and small integers;
collect several positions, filter candidates, and let the quiz endpoint
tell you when you are right. The quiz then asks for the byte offset you
measured earlier, tying both halves together. Answer both correctly and
the kiosk prints your flag, no memory corruption required.
