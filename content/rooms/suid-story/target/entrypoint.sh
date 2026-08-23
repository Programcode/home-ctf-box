#!/bin/sh
# Room entrypoint: prepares the box and runs the SSH server.
set -eu

FLAG="${ROOM_FLAG:-FLAG{FLAGNOTSET0000000000000000}}"

umask 022
printf '%s\n' "$FLAG" > /root/flag.txt
chmod 600 /root/flag.txt

# The notes file reportgen's dump mode was originally pointed at.
printf '%s\n' 'quarterly numbers pending, see finance dashboard' > /root/notes.txt
chmod 600 /root/notes.txt

printf '%s\n' \
  '=== OpenRange Training Box ===' \
  'This machine is a simulated lab target. Never reuse lab credentials elsewhere.' \
  'Lab account: learner / learner' \
  > /etc/motd

ssh-keygen -A >/dev/null

exec /usr/sbin/sshd -D -e
