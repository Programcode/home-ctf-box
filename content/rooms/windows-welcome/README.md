# windows-welcome

Beginner guided Windows-track room, honestly Linux-hosted. Learners
SSH in (learner/learner) to a Debian box whose login shell is real
PowerShell 7 with a fake Windows identity (WIN-SIM01) and a ~/winfs
tree standing in for C:. Teaches Get-Command, Get-Help, Get-ChildItem,
Select-String; flag found by targeted search of the simulated Users
tree. Points: 100.

- `room.yaml` declares objectives, scope, safety, elevated target
  (sshd), tasks.
- `lesson/` states plainly which parts are real (pwsh) and which are
  simulated (computer name, C: layout).
- `target/` builds the Debian SSH box (port 22) with PowerShell LTS
  from the Microsoft repo and recreates winfs on every boot.
- `solver/solver.py` proves the intended path end to end with
  paramiko driving pwsh.

Verify locally with `cyberrange solve content/rooms/windows-welcome`.
