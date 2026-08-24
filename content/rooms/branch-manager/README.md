# branch-manager

Easy challenge reversing room. The license checker at
`/opt/challenges/license-check` advertises a master key format in its
banner, but the constant behind that comparison was corrupted at build
time so the advertised key never works. The live route into the granted
branch is three numeric checks whose immediate values appear only in
`/opt/challenges/notes.asm`, an objdump captured during the image build.
Learners read control flow, separate the dead comparison from the live
ones, craft a key from the constants, and take the branch that prints.

- `room.yaml` declares objectives, scope, safety, target, tasks.
- `lesson/` holds the learner-facing brief.
- `target/` builds the Debian SSH box (port 22, learner/learner) and
  generates notes.asm at build time with objdump -d.
- `solver/solver.py` proves the intended path end to end with paramiko:
  it parses the verify_key section out of notes.asm, derives a key from
  the three cmp immediates, and submits it.

Verify locally with `cyberrange solve content/rooms/branch-manager`.
