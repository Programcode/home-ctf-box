# share-and-share-alike

Beginner guided Windows-track room, honestly Linux-hosted. A real
smbd serves \\SIMFILE01\public (browseable) and a hidden dev$ share
(browseable=no, valid users smbuser). Public meeting notes leak the
dev$ name plus working credentials. Because the workstation image
lacks an SMB client, a small Flask HTTP mirror of the same
directories (with mirrored auth) stands in for smbclient; the lesson
shows the real commands. Flag sits in dev$/deploy-notes.txt. Points: 125.

- `room.yaml` declares objectives, scope, safety, elevated target
  (smbd needs port 445 + privsep), tasks.
- `lesson/` discloses the simulation seams and teaches hidden-is-not-
  protected.
- `target/` builds Debian + samba + Flask mirror (ports 8000, 445);
  entrypoint recreates share contents every boot.
- `solver/solver.py` proves the intended path with httpx: enumerate
  public files, parse leaked creds, authenticate to dev$, read flag.

Verify locally with `cyberrange solve content/rooms/share-and-share-alike`.
