# token-gesture

Medium challenge Windows-track room, honestly Linux-hosted. A simulated
token store at /opt/tokens (plain JSON stand-ins with integrity and
group fields plus a documented sha256 checksum) feeds a root helper
called tokentool, granted to learner through a single sudo entry. The
helper trusts any verifiable token it finds in the world-writable cache
at /var/cache/tokentool, so learners forge a high-integrity DOMAIN
ADMINS-SIM token, plant it there, and collect the flag the helper reads
from /root/flag.txt. Points: 250.

- `room.yaml` declares objectives, scope, safety, elevated target
  (sshd), tasks.
- `lesson/` discloses every simulated part and teaches why token
  provenance beats internal consistency checks.
- `target/` builds the Debian SSH box (port 22, learner/learner) with
  the token store, world-writable cache, and sudo-granted tokentool.
- `solver/solver.py` proves the intended path with paramiko: read the
  schema, compute a valid checksum, plant the forged token, assume it.

Verify locally with `cyberrange solve content/rooms/token-gesture`.
