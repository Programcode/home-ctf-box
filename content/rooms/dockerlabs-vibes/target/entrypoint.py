#!/usr/bin/env python3
"""Room entrypoint: seed hostsim, flags and run the SSH server."""

import os
import subprocess

FLAG = os.environ.get("ROOM_FLAG", "FLAGNOTSET0000000000000000")

os.umask(0o022)

os.makedirs("/hostsim/root", exist_ok=True)
os.makedirs("/hostsim/var/log", exist_ok=True)
with open("/hostsim/root/flag.txt", "w", encoding="utf-8") as fh:
    fh.write(FLAG + "\n")
os.chmod("/hostsim/root/flag.txt", 0o600)
os.chmod("/hostsim/root", 0o700)
os.chown("/hostsim/root", 0, 0)
with open("/hostsim/var/log/app.log", "w", encoding="utf-8") as fh:
    fh.write("2026-08-14 vault sync ok\n2026-08-15 rotation pending\n")
os.chmod("/hostsim/var/log/app.log", 0o644)

hostname_bin = None
for candidate in ("/bin/hostname", "/usr/bin/hostname"):
    if os.path.exists(candidate):
        hostname_bin = candidate
        break
if hostname_bin:
    host = subprocess.run([hostname_bin], capture_output=True, text=True).stdout.strip()
    with open("/etc/hosts", "a+", encoding="utf-8") as hosts:
        hosts.seek(0)
        if f" {host}" not in hosts.read():
            hosts.write(f"127.0.0.1 {host}\n")

with open("/etc/motd", "w", encoding="utf-8") as motd:
    motd.write(
        "=== OpenRange Training Box ===\n"
        "This machine is a simulated lab target. Never reuse lab credentials elsewhere.\n"
        "Lab account: learner / learner (see README.first in your home)\n"
    )

subprocess.run(["ssh-keygen", "-A"], check=True, capture_output=True)
os.execv("/usr/sbin/sshd", ["/usr/sbin/sshd", "-D", "-e"])
