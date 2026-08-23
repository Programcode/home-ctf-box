# Paper Permissions

Locking a file down only works if every copy of it gets the same care.
This box runs an appwatch agent whose live configuration in /etc/app.conf
is properly locked to root. The same root process also keeps a rolling
backup in /var/backups, and nobody ever checked what mode that copy ends
up with. Your job is to notice the gap by looking, not forcing.

## What you will practice

- Reading ls -l output: owner, group, mode bits, and what they permit.
- Enumerating standard backup locations instead of guessing paths.
- Treating a permission denied error as a hint about where else the
  data might live.

## Scope

Only the box at `ssh://target:22` is in scope. Nothing outside your lab
instance is a target. You do not need any exploit tooling here: the
permissions themselves hand you the secret once you find the copy.
