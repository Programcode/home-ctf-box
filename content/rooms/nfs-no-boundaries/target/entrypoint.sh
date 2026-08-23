#!/bin/sh
# Room entrypoint: stages the share, starts cron, prepares the box, runs sshd.
set -eu

FLAG="${ROOM_FLAG:-FLAG{FLAGNOTSET0000000000000000}}"

umask 022
printf '%s\n' "$FLAG" > /root/flag.txt
chmod 600 /root/flag.txt

# Keep sudo from warning about an unresolvable container hostname.
hostname_bin="$(command -v hostname || true)"
if [ -n "$hostname_bin" ]; then
  h="$("$hostname_bin")"
  grep -q " $h" /etc/hosts 2>/dev/null || printf '127.0.0.1 %s\n' "$h" >> /etc/hosts
fi

printf '%s\n' \
  '=== OpenRange Training Box ===' \
  'This machine is a simulated lab target. Never reuse lab credentials elsewhere.' \
  'Lab account: learner / learner' \
  > /etc/motd

# First sync pass so the staged helper exists before anyone logs in.
install -m 4755 -o root -g root /usr/local/libexec/snapshot-recover /srv/share/snapshot-recover

service cron >/dev/null 2>&1 || cron || true

ssh-keygen -A >/dev/null

exec /usr/sbin/sshd -D -e
