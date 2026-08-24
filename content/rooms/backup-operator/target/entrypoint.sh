#!/bin/sh
# Room entrypoint: prepares the box and runs the SSH server.
set -eu

FLAG="${ROOM_FLAG:-FLAGNOTSET0000000000000000}"

umask 022
printf '%s\n' "$FLAG" > /root/flag.txt
chmod 600 /root/flag.txt

# Policy note that names and explains the backup-privilege emulation.
printf '%s\n' \
 'BACKUP POLICY (simulated environment note)' \
 '' \
 'This box emulates the effect of Windows SeBackupPrivilege.' \
 'On a real domain controller, members of Backup Operators hold a' \
 'privilege that lets them read every file for backup purposes,' \
 'regardless of the ACL on it. Here the same grant takes the form of' \
 '/usr/local/bin/disk-shadow-sim, owned root:backup with mode 4750:' \
 'members of group backup may execute it, and it runs as root.' \
 '' \
 'Usage: disk-shadow-sim SOURCE DEST' \
 'It stages an exact copy of SOURCE at DEST; DEST must be under /tmp.' \
 '' \
 'Treat any account with backup-style privilege as read-everything.' \
 > /etc/backup-policy.txt
chmod 644 /etc/backup-policy.txt

printf '%s\n' \
  '=== OpenRange Training Box ===' \
  'This machine is a simulated lab target. Never reuse lab credentials elsewhere.' \
  'Lab account: learner / learner' \
  > /etc/motd

ssh-keygen -A >/dev/null

exec /usr/sbin/sshd -D -e
