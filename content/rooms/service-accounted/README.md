# service-accounted

Easy challenge Windows-track room, honestly Linux-hosted. A root-owned
JSON database at /opt/services/services.json stands in for Service
Control Manager registry data; a root shell loop executes each Running
service's recorded payload every 30 seconds. One payload lives in a
group-writable directory, mirroring the writable-service-path abuse
mechanic. Learners audit, spot the flaw, append a flag copy to the
payload, and collect from /tmp/flag.out. Points: 200.

- `room.yaml` declares objectives, scope, safety, elevated target
  (sshd), tasks.
- `lesson/` discloses exactly what is simulated (SCM loop, JSON
  database) versus real Unix permissions doing the work.
- `target/` builds the Debian SSH box (port 22); entrypoint resets the
  payload and outputs every boot.
- `solver/solver.py` proves the intended path with paramiko, polling
  one full scheduler period.

Verify locally with `cyberrange solve content/rooms/service-accounted`.
