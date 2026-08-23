#!/bin/sh
# Room entrypoint: drops the real flag outside the jail, plants the decoy
# inside it, and runs sshd.
set -eu

FLAG="${ROOM_FLAG:-FLAG{FLAGNOTSET0000000000000000}}"

umask 022
printf '%s\n' "$FLAG" > /flag.txt
chown root:root /flag.txt
chmod 644 /flag.txt

printf '%s\n' 'FLAG{JAILDEC0YCOPY0000000}' > /jail/flag.txt
chown root:root /jail/flag.txt
chmod 644 /jail/flag.txt

printf '%s\n' \
  '=== OpenRange Training Box ===' \
  'This machine is a simulated lab target. Never reuse lab credentials elsewhere.' \
  'Lab account: learner / learner' \
  '' \
  'Scenario notice: your login session is placed inside a chroot sandbox at' \
  '/jail by the elevated helper /usr/local/bin/jailctl. The helper supports' \
  'an administrative subcommand: jailctl chroot NEWROOT [COMMAND...].' \
  > /etc/motd

ssh-keygen -A >/dev/null

exec /usr/sbin/sshd -D -e
