# quiet-persistence

Hard investigation room. SSH in as the analyst, sweep the box for all
four persistence artifacts (cron drop-in, beaconing shell init file,
rogue loop script in /usr/local/sbin, custom systemd unit), then file
their paths to the local report endpoint for verification and the
flag. Points: 300.

- `room.yaml` declares objectives, scope, safety, target, tasks.
- `lesson/` holds the learner-facing brief.
- `target/` builds the Debian box: sshd on 22 (analyst/analyst), four
  inert persistence artifacts planted by the entrypoint, a harmless
  heartbeat loop appending to /tmp/.beacon.log only, and a python3
  stdlib report endpoint bound to 127.0.0.1:8000.
- `solver/solver.py` proves the intended path end to end over
  paramiko: discover each artifact with standard sweeps, then POST
  the findings list to the endpoint and capture the verified flag.

Nothing malicious executes anywhere in this image; every mechanism
only prints timestamped lines to a local log.

Verify locally with `cyberrange solve content/rooms/quiet-persistence`.
