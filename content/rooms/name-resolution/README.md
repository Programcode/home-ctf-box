# name-resolution

Easy challenge Windows-track room, honestly Linux-hosted. A
responder-sim daemon on loopback UDP 5355/137 logs name queries and
claims exactly one name from the simulated site inventory (FILESRV01),
answering with a deterministic, clearly labeled fake NTLMv2-SIM blob.
Learners run the provided query client over SSH, read the capture log
in the /srv/public share stand-in, and submit the SIM-HASH value to the
checker endpoint on port 8000 for the flag. Points: 175.

- `room.yaml` declares objectives, scope, safety, elevated target
  (sshd plus checker), tasks.
- `lesson/` discloses every simulated part and teaches why legacy
  fallback name resolution invites poisoning.
- `target/` builds the Debian box: sshd (port 22), responder-sim,
  checker page (port 8000), learner tools, inventory and logs.
- `solver/solver.py` proves the intended path with paramiko plus httpx:
  run the client, lift the blob from the reply or log, submit it.

Verify locally with `cyberrange solve content/rooms/name-resolution`.
