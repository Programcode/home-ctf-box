# Services Everywhere

Easy box room. A multi-service appliance where an anonymous file drop
on 2121 leaks the credentials for an application manager console on
8080, and the console's one documented deploy action publishes a copy
of the flag. Points: 250.

- `room.yaml` declares objectives, scope, safety, target, tasks.
- `lesson/` holds the learner-facing brief.
- `target/` builds the Debian box: sshd on 22, the FTP-like file drop
  on 2121, and the manager console simulator on 8080. The deploy
  action copies a flag string between two files; nothing executes.
- `solver/solver.py` proves the intended path end to end with raw
  sockets and HTTP from the attacker image.

Verify locally with `cyberrange solve content/rooms/services-everywhere`.
