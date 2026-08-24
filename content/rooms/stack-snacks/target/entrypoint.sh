#!/bin/sh
# Room entrypoint: prepares the box, starts the kiosk service, runs sshd.
set -eu

FLAG="${ROOM_FLAG:-FLAGNOTSET0000000000000000}"

umask 022
printf '%s\n' "$FLAG" > /root/flag.txt
chmod 600 /root/flag.txt

printf '%s\n' \
  '=== OpenRange Training Box ===' \
  'This machine is a simulated lab target. Never reuse lab credentials elsewhere.' \
  'Lab account: learner / learner' \
  'Local service: snack-vendor kiosk listens on 127.0.0.1:9994 and inside the lab.' \
  > /etc/motd

# Keep one long-lived kiosk process so its stack canary stays stable
# across connections; restart it if it ever exits.
(
  while true; do
    /opt/challenges/snack-vendor >> /var/log/snack-vendor.log 2>&1 || true
    sleep 1
  done
) &

ssh-keygen -A >/dev/null

exec /usr/sbin/sshd -D -e
