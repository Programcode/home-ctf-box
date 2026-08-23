# shared-secrets

Medium challenge room. Recover a stale service-account password from
an old ops note, enumerate local accounts, and walk the credential
into the archivist session through su to read the records room flag.
Points: 250.

- `room.yaml` declares objectives, scope, safety, target, tasks.
- `lesson/` holds the learner-facing brief.
- `target/` builds the Debian box: sshd on 22 (learner/learner), a
  records-custodian archivist account that reuses the retired backup
  password, and an nologin svc_backup service account.
- `solver/solver.py` proves the intended path end to end over
  paramiko: read the note, enumerate shells from /etc/passwd, then su
  through an interactive PTY and read the flag.

Verify locally with `cyberrange solve content/rooms/shared-secrets`.
