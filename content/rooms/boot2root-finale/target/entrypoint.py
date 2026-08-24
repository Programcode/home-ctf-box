#!/usr/bin/env python3
"""Room entrypoint: seed flags, drop the gatekeeper privileges, run sshd."""

import os
import pwd
import subprocess

FLAG = os.environ.get("ROOM_FLAG", "FLAGNOTSET0000000000000000")
GATEKEEPER_USER = "gatekeep"

os.umask(0o022)

with open("/root/flag.txt", "w", encoding="utf-8") as fh:
    fh.write(FLAG + "\n")
os.chmod("/root/flag.txt", 0o600)

svc = pwd.getpwnam(GATEKEEPER_USER)
subprocess.Popen(
    ["python3", "/opt/gatekeeper/knock_share.py"],
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
    user=svc.pw_uid,
    group=svc.pw_gid,
)

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
    )

subprocess.run(["ssh-keygen", "-A"], check=True, capture_output=True)
os.execv("/usr/sbin/sshd", ["/usr/sbin/sshd", "-D", "-e"])
