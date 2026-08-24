# directory-recovery

Hard investigation Windows-AD tabletop room. A locked Flask container
serves an evidence pack: a ransom note that timestamps the compromise,
two ntds-sim dump fragments listing directory accounts with creation
and change times, and a backups inventory. Learners identify accounts
created or modified post-compromise, choose the one backup that is both
pre-compromise and verified offline, and POST the full recovery plan to
/recover, which grades all three parts and returns the flag on a
complete match. Points: 300.

- `room.yaml` declares objectives, scope, safety, target, tasks.
- `lesson/` holds the learner-facing brief.
- `target/` builds the locked container; evidence is deterministic.
- `solver/solver.py` derives rogue accounts and restore source from the
  evidence with httpx.

Single-container disclosure: no real ransomware exists here; nothing
encrypts and no payload executes.

Verify locally with `cyberrange solve content/rooms/directory-recovery`.
