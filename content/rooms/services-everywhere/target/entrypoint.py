#!/usr/bin/env python3
"""Room entrypoint: seed shares and flags, start unprivileged sims, run sshd."""

import os
import pwd
import subprocess
import time

FLAG = os.environ.get("ROOM_FLAG", "FLAGNOTSET0000000000000000")
DROP_USER = "svcdrop"

WELCOME = """Services Everywhere appliance, anonymous file drop.

This share is read only for guests. Old deployment paperwork tends to
pile up here; housekeeping is on the roadmap.
"""

DEPLOY_NOTES = """Deployment notes, application manager console (internal)

From: infra team
Re: rotating console credentials

The manager console lives on port 8080 under /manager/html. Until the
rotation ticket lands, sign in as:

    username: manager
    password: deploy1994

The console exposes exactly one documented action: deploying the
flagcopy artifact, which republishes a copy of the application flag to
the web tree so monitoring can verify it. Do not leave this note in the
guest share after rotation.
"""

TODO = """housekeeping list:
- rotate manager console password (ticket INFRA-221)
- retire the guest file drop or at least clean it
- stop writing passwords into plaintext notes (see INFRA-221)
"""


def drop(path: str, content: str, mode: int) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)
    os.chmod(path, mode)


def main() -> None:
    os.umask(0o022)
    svc = pwd.getpwnam(DROP_USER)

    drop("/root/root.txt", FLAG + "\n", 0o600)

    app_dir = "/opt/services-everywhere"
    app_secret = f"{app_dir}/app.flag"
    os.chown(app_dir, svc.pw_uid, svc.pw_gid)
    os.chmod(app_dir, 0o750)
    drop(app_secret, FLAG + "\n", 0o600)
    os.chown(app_secret, svc.pw_uid, svc.pw_gid)

    drop("/srv/ftpd/pub/WELCOME.TXT", WELCOME, 0o644)
    drop("/srv/ftpd/pub/deploy-notes.txt", DEPLOY_NOTES, 0o644)
    drop("/srv/ftpd/pub/housekeeping.txt", TODO, 0o644)

    for script in ("ftp_sim.py", "manager_sim.py"):
        subprocess.Popen(
            ["python3", f"{app_dir}/{script}"],
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
            "Lab account: learner / learner\n"
        )

    subprocess.run(["ssh-keygen", "-A"], check=True, capture_output=True)
    time.sleep(1)
    os.execv("/usr/sbin/sshd", ["/usr/sbin/sshd", "-D", "-e"])


if __name__ == "__main__":
    main()
