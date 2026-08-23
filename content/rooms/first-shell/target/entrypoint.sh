#!/bin/sh
# Room entrypoint: prepares the learner box and runs the SSH server.
set -eu

FLAG="${ROOM_FLAG:-FLAGNOTSET0000000000000000}"

# The objective lives in the learner account's own home directory.
umask 022
printf '%s\n' "$FLAG" > /home/learner/flag.txt
chown learner:learner /home/learner/flag.txt
chmod 600 /home/learner/flag.txt

# Connect banner carries the lab credentials so nobody gets stuck.
printf '%s\n' \
  '=== OpenRange Training Box ===' \
  'This machine is a simulated lab target. Never reuse lab credentials elsewhere.' \
  'Lab account: learner / learner' \
  'Your objective sits somewhere in this home directory.' \
  > /etc/motd

ssh-keygen -A >/dev/null

exec /usr/sbin/sshd -D -e
