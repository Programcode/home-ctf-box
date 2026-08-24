# return-address

Hard challenge binary fundamentals room. The toy target
`/opt/challenges/ropebridge` is statically linked, stripped, compiled
with no PIE and no stack protector, and reads past its 64-byte buffer;
NX remains on, so the honest solution is a ret2win ROP chain, never
shellcode. The build captured `/opt/challenges/symbols.txt` (pre-strip
nm map) and `/opt/challenges/dump.asm` (focused objdump) before
stripping, so every address is derivable on the box.

- `room.yaml` declares objectives, scope, safety, target, tasks.
- `lesson/` holds the learner-facing brief.
- `target/` builds the Debian SSH box (port 22, learner/learner); the
  Dockerfile generates symbols.txt and dump.asm mid-build.
- `solver/solver.py` proves the intended path end to end with paramiko:
  parses symbols.txt for win, dump.asm for the raw pop rdi; ret gadget
  and a bare ret alignment byte, reads the banner depth for padding,
  and delivers the packed chain base64-encoded over stdin.

Verify locally with `cyberrange solve content/rooms/return-address`.
