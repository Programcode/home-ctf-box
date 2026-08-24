# APK Breadcrumbs

Easy challenge room for Android-style static analysis. The package at
/evidence is a synthetic zip with a text dex stub, so the whole first
pass an analyst runs against a real APK happens with stdlib zipfile and
regex. Points: 175.

- `room.yaml` declares objectives, scope, safety, target, tasks.
- `lesson/` covers APK anatomy and the apktool/jadx mental model.
- `target/` builds the package desk (Flask, port 8000).
- `solver/solver.py` proves the unpack, extract, verify path end to end.

The archive is generated in-image with fixed timestamps and contains
no real application or endpoint. Verify locally with
`cyberrange solve content/rooms/apk-breadcrumbs`.
