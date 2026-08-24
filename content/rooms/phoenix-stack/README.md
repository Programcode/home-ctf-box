# Phoenix Stack

Medium challenge room. A five-stage stack and format-string ladder in
the classic exploitation-ladder tradition, served over one raw TCP
port. Each stage prints its own memory map and grades the payload;
the flag prints after the fifth pass. Nothing executes; graders
compare bytes against maps. Points: 275.

- `room.yaml` declares objectives, scope, safety, target, tasks.
- `lesson/` holds the learner-facing brief.
- `target/` builds a locked alpine container running the ladder on
  tcp/4000: overflow ret2win, canary carry, positional format-string
  read, counted %n write, ret2libc-style chain assembly.
- `solver/solver.py` proves the intended path end to end with one raw
  socket connection, parsing every map before answering each rung.

Verify locally with `cyberrange solve content/rooms/phoenix-stack`.
