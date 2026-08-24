# return-address

Return-oriented programming sounds exotic until you do it once by hand
on a target built for learning. This room is that target: every
mitigation that makes return chains painful has been deliberately left
off, while NX stays on so the answer is a chain of existing code
fragments rather than injected shellcode. Working through it teaches
the full workflow, from reading a symbol map to packing addresses in
little-endian order, that scales up to real-world binary analysis.

## Why disabled mitigations change everything

Without PIE, the binary loads at the same fixed addresses on every run,
so any address you discover today still works tomorrow and inside your
solver. Without a stack canary, bytes you write past the buffer reach
the saved return address unchallenged. With the stack protector off and
a static link, nothing interrupts the classic overflow arithmetic, and
gadget hunting happens entirely inside one predictable file. NX remains
enabled, which is the honest middle ground: you cannot execute anything
you place on the stack, but you fully control where execution returns.
That constraint is what makes ROP the canonical answer.

## Reading the artifacts

Two files survived the strip. symbols.txt maps function names captured
before stripping to their fixed addresses, including win and two named
gadget functions. dump.asm disassembles exactly those functions, and it
deserves a careful reading, because compiler-generated frame setup sits
at the top of every function. The function labeled as your gadget does
contain pop rdi; ret, but entering it at the symbol address executes
push rbp first and ruins the chain; the usable gadget is the address of
the pop instruction itself, one step into the function. That gap between
a symbol and its useful bytes is exactly what real gadget hunting is
about. The banner discloses the buffer depth, and on x86-64 an
eight-byte saved frame pointer always sits between a buffer's end and
the saved return address.

## Assembling and delivering the chain

The chain reads from low to high like a tiny program written in return
addresses: filler to reach the saved slot, the pop rdi gadget (which
loads the next quadword into rdi and rets onward), the magic constant
win demands, a bare ret byte, and win itself. Raw bytes do not survive
shell pipelines cleanly, so professionals base64-encode payloads and
decode them at the far end, a habit this room rewards. The extra ret is
not decoration: each executed ret shifts the stack by eight bytes, and
win's printf assumes the sixteen-byte alignment the calling convention
promises, so an odd number of gadget rets keeps that promise. Feed the
finished chain in, let the read loop drain stdin, and climb's return
instruction slides into your program written in addresses.
