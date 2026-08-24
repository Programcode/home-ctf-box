# Firmware Pantry

Medium challenge room for firmware extraction practice. The image at
/evidence is a synthetic container with a documented stub, custom
magic, and an embedded xz-compressed tar root filesystem, followed by
an offline SHA-256 wordlist crack and an admin login. Points: 275.

- `room.yaml` declares objectives, scope, safety, target, tasks.
- `lesson/` covers magic scanning, shadow mechanics, and hash cracking.
- `target/` builds the firmware desk (Flask, port 8000).
- `solver/solver.py` proves slice, extract, crack, login end to end.

The image is assembled in-image from strings plus stdlib tarfile/lzma
and contains no real vendor code. Verify locally with
`cyberrange solve content/rooms/firmware-pantry`.
