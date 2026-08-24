#!/bin/sh
# Simulated Service Control Manager pass: runs each Running service's
# payload exactly as recorded in the services database. Root-only.
set -eu

python3 - <<'PY'
import json
import os
import subprocess

with open("/opt/services/services.json", encoding="utf-8") as fh:
    services = json.load(fh)

for svc in services:
    if svc.get("state") != "Running":
        continue
    path = svc.get("linux_sim_path")
    if path and os.path.isfile(path):
        subprocess.run(["/bin/sh", path], check=False)
PY
