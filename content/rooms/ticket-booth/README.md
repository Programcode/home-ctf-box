# ticket-booth

Hard challenge Windows-track room, honestly Linux-hosted. A locked
Flask app plays a fake KDC: two registered SPNs under fictional service
accounts, tickets whose enc-part is base64 over plaintext XORed with a
repeating sha256(password) keystream (deliberately toy XOR-SIM-v1, not
RC4-HMAC; documented on /kdc/docs with the exact 48-byte preamble).
Learners request tickets with a provided stdlib getuserspns.py
equivalent, run the known-plaintext wordlist crack to recover
svc_sql's password, and open /kdc/admin via Basic auth for the flag.
Points: 275.

- `room.yaml` declares objectives, scope, safety, locked target, tasks.
- `lesson/` discloses the toy cipher and teaches why real kerberoasting
  succeeds or fails.
- `target/` builds a python:3.12-alpine Flask KDC (port 8000, locked
  profile) with SPN list, ticket issuance, docs, tooling, wordlist, and
  Basic-auth admin console.
- `solver/solver.py` proves the intended path with httpx plus stdlib:
  download and run the provided client, crack both tickets from the
  published wordlist, authenticate as svc_sql.

Verify locally with `cyberrange solve content/rooms/ticket-booth`.
