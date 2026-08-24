# Heap House

Heap exploitation has a reputation as the deep end of binary security,
and most of that difficulty comes from the environment: debuggers,
ASLR, version-sensitive libc offsets, and crashes that wipe your
progress. Heap House removes the environment and keeps the ideas. The
service in front of you models a small bump allocator with a
tcache-style recycling path, exposed over JSON endpoints that behave
like malloc and free. It ships one deliberate bug: freed chunks stay
readable and writable. Your job is to turn that use-after-free into an
arbitrary write and flip the win variable at 0x20000.

Be clear about what this is. Nothing here runs a real exploit. The
heap is a Python dictionary, addresses are sequential integers printed
on the page, and the flag comes from an endpoint check rather than a
corrupted return path. What transfers to real targets is the state
machine you rehearse: bin order, fd pointers, why two frees give you a
predictable layout, and what the allocator does when it trusts metadata
an attacker could edit.

## How a real heap gets here

glibc keeps a per-thread cache of recently freed chunks called tcache:
one singly linked list per size class, at most seven entries, last in
first out. Each free pushes the chunk onto its bin and writes the
previous top address into the chunk's first data slot, the fd pointer.
Each malloc pops the top entry and promotes whatever that slot points
to as the new head. The cache exists for speed, which is why it trusts
metadata so completely: reading a pointer and re-linking it is all the
fast path does before returning memory to the application.

That trust is exactly what a use-after-free breaks. If a program frees
a chunk but keeps a dangling reference it still writes through, the
attacker controls bytes inside a chunk the allocator considers dead but
still linked. Overwrite the fd slot and you have rewritten the
allocator's idea of where its own free list lives. The classic chain
frees two same-size chunks so the second free's fd holds the first
chunk's address, then uses the dangling write to replace that fd with
the address you want allocated next. Two allocations later, malloc
hands back a pointer to attacker-chosen memory. In this room that
memory holds the win variable; on real targets of the 2010s it held
__free_hook or a function pointer table.

## The chain, step by step

Start by reading /api/state after every move; the event log names every
operation, including uaf-write labels when a store lands on freed
memory. Allocate c1 and c2 at 64 bytes. Free c2, then c1. The class 64
bin now reads [c2, c1] from bottom to top, and c1's fd slot holds
0x10080 because that was the previous top. This ordering detail is the
whole game: if you had freed c1 first, the poison would land on the
wrong entry and the chain would hand you c2 instead.

With the bin stacked correctly, POST a write to c1 at offset 0 with
value 0x20000. The service accepts it and marks it a uaf-write, which
is your proof the dangling primitive fired. Now allocate twice. The
first malloc pops c1 and finds its fd no longer matches the rest of
the bin, so it promotes 0x20000 to the head and tells you so in the
promoted_fd field. The second malloc pops that promoted value,
discovers nobody owns the address, mints a forged chunk there, and
returns it to you. Write the magic 0xC0FFEE000001 through the forged
chunk id and GET /api/win pays out. Every response documents why it
happened, so when something surprises you, the log explains it.

## What the simulator leaves out

Modern glibc defends this exact chain in two ways, and the lesson is
honest about both. Safe-linking, introduced in glibc 2.32, mangles
every stored fd by XORing it with the chunk's own address shifted;
your poisoned pointer would decode to garbage unless you first leak a
heap address and pre-mangle your fake fd to compensate. That is why
contemporary chains start with an infoleak. Second, tcache_get checks
alignment on the chunk it returns, so a fake pointer must be 16-byte
aligned; the simulator enforces that check and will abort with the
real error text if you feed it an unaligned target. There are no
double-free protections to bypass here beyond the key check, and no
unsorted-bin or largebin mechanics at all.

When you finish, replay the run mentally against a real allocator:
same steps, plus a heap leak, plus mangling arithmetic, plus a target
worth writing to. The simulator gives you the choreography; real
targets add stagecraft. If you want the genuine article afterward, the
how2heap repository teaches these primitives against actual glibc in a
lab you control.
