# quoted-intentions

Easy challenge Windows-track reasoning room, honestly Linux-hosted. A
Flask page simulates service enumerator output (sc qc style) with one
unquoted binPath containing spaces. Learners derive the CreateProcess
resolution order (C:\Program.exe, C:\Program Files\Unquoted.exe, full
path) and submit it to /check; the exact ordered chain returns the
flag. No privesc anywhere. Points: 150.

- `room.yaml` declares objectives, scope, safety (locked profile),
  tasks.
- `lesson/` discloses the simulation plainly and teaches resolution
  semantics.
- `target/` builds a locked Flask container (port 8000).
- `solver/solver.py` proves the intended path with httpx.

Verify locally with `cyberrange solve content/rooms/quoted-intentions`.
