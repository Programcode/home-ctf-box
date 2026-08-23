#!/bin/sh
# Room entrypoint: plants the stale ops note and the archives, runs sshd.
set -eu

FLAG="${ROOM_FLAG:-FLAG{FLAGNOTSET0000000000000000}}"

umask 022
printf '%s\n' "$FLAG" > /var/archives/flag.txt
chown archivist:archivist /var/archives/flag.txt
chmod 640 /var/archives/flag.txt
mkdir -p /var/archives/incoming
chown svc_backup:svc_backup /var/archives/incoming

cat > /home/learner/shared-creds.txt <<'EOF'
# ops handoff note, recovered from the 2025 backup rotation checklist
#
# service account credentials as of last audit (rotate after cutover):
#   svc_backup : vEry0ld-backup-PW
#
# NOTE(dana): this account was supposed to be retired with the old
# tape library. if anything still authenticates with it, that is a
# finding, not a feature.
EOF
chown learner:learner /home/learner/shared-creds.txt

printf '%s\n' \
  '=== OpenRange Training Box ===' \
  'This machine is a simulated lab target. Never reuse lab credentials elsewhere.' \
  'Lab account: learner / learner' \
  > /etc/motd

ssh-keygen -A >/dev/null

exec /usr/sbin/sshd -D -e
