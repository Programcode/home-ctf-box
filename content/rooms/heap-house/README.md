# Heap House

Insane range room, the track D heap capstone. A Flask service simulates
a glibc-style allocator with a tcache fast path and an intentional
use-after-free, so the full poisoning chain can be studied without any
real memory corruption. Points: 500.

- `room.yaml` declares objectives, scope, safety, target, tasks.
- `lesson/` walks the chain and maps each step to real glibc mechanics.
- `target/` builds the allocator simulator (Flask, port 8000).
- `solver/solver.py` proves UAF to fd poison to arbitrary write end to end.

Everything in this room is synthetic: the heap is a Python dictionary,
addresses are sequential integers, and no executable exploit exists
anywhere. Verify locally with `cyberrange solve content/rooms/heap-house`.
