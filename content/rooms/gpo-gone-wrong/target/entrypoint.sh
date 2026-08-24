#!/bin/sh
# Room entrypoint: drops the root flag, starts the GPO policy loop, and
# runs the SSH server.
set -eu

FLAG="${ROOM_FLAG:-FLAGNOTSET0000000000000000}"

umask 022
printf '%s\n' "$FLAG" > /root/flag.txt
chmod 600 /root/flag.txt

printf '%s\n' \
  '=== OpenRange Training Box ===' \
  'This machine is a simulated lab target. Never reuse lab credentials elsewhere.' \
  'Lab account: learner / learner' \
  'Simulated SYSVOL: /srv/sysvol-sim (GPO task definitions, read-only share model)' \
  > /etc/motd

python3 /usr/local/sbin/gpo-task-runner.py &

ssh-keygen -A >/dev/null

exec /usr/sbin/sshd -D -e
