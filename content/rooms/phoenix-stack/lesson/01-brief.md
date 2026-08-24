# Phoenix Stack

Memory-corruption exploitation looks like magic until you build it
byte by byte, and every serious binary training curriculum has
converged on the same teaching device: a ladder of small stages, each
one printing its own memory map, each one refusing to open until your
payload is exactly right. The tradition runs through community
exploit-education stacks and vulnerable-VM ladders alike because it
works. This room rebuilds that ladder as a pure TCP protocol so you
can climb it with nothing but a socket and a struct module.

## What you will practice

The first two rungs teach stack shape. Stage 1 is the founding trick
of the whole discipline: fill a fixed buffer, then overwrite exactly
the saved return address with the address of a win function. Stage 2
adds the modern defense that changed everything: a stack canary sits
between your filler and the return address, and the map hands you its
value this round. Real attackers recover canaries through leaks;
here you practice the equally important half of the skill, which is
reading a layout precisely and keeping one value intact while
rewriting another. Little-endian packing stops being a chore and
becomes muscle memory.

The next two rungs teach format strings without a debugger. A format
string bug lets an attacker walk the stack as if it were an array,
and stage 3 makes that literal: ten numbered slots are printed, one
holds the round's magic word, and you must write the positional
specifier that reads it back. Stage 4 turns the same primitive into a
write: the engine counts literal characters before a %n directive and
stores that count, so hitting the target value means engineering your
own padding length. That read-then-write progression is exactly how
real format string exploits bootstrap arbitrary memory access.

Stage 5 closes the loop with return-to-libc. You get three addresses,
a pop rdi gadget, a /bin/sh string, and the system PLT entry, and you
must order them the way a real chain would execute: gadget first so
the argument register loads before control transfers. Assemble them
backwards and the chain fails; assemble them forwards and you have
reproduced, in miniature, the call chain behind decades of CTF
solutions.

## Scope

Only tcp/4000 on your own lab instance is in scope, and one
connection is enough for the whole climb. The service runs in a
locked container: no capabilities, no privilege escalation, no memory
corruption anywhere in the implementation. Every grader compares your
bytes against the printed maps, which keeps the room safe while
preserving the exact mental motions that real stack exploitation
demands. If a payload fails a rung, the server tells you which
property missed and closes the connection; you reconnect, the ladder
resets, and you try again with better notes.

The flag appears only after all five rungs pass in one session, so
partial progress never leaks the answer and guessing cannot carry you
upward. That single-session design is deliberate: real exploitation
chains break if any intermediate step is wrong, and practicing with
that constraint builds the habit of validating each stage before
building on it. Nothing you send can crash or corrupt anything; the
worst outcome of a wrong payload is a closed socket. Work in small
increments, keep a scratchpad of the addresses each map prints, and
remember that every value you need is on the screen by design. The
skill under test is translation precision, not secret knowledge.
