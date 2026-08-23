#!/bin/sh
# Room entrypoint: appwatch service config plus the leaky backup loop.
set -eu

FLAG="${ROOM_FLAG:-FLAGNOTSET0000000000000000}"

# The service's real config: root-owned and closed to everyone else.
umask 077
mkdir -p /etc
printf '%s\n' \
  '# appwatch monitoring agent configuration' \
  'listen_port = 8443' \
  'log_level = warn' \
  "deploy_token = $FLAG" \
  > /etc/app.conf
chmod 600 /etc/app.conf

umask 022
# The ops team's backup habit: root snapshots its own config into
# /var/backups every 30 seconds and never checks the resulting mode.
# The first copy is written synchronously so the backup exists before
# sshd starts accepting sessions.
cp /etc/app.conf /var/backups/.app.conf.tmp
chmod 644 /var/backups/.app.conf.tmp
mv /var/backups/.app.conf.tmp /var/backups/app.conf

(
  while :; do
    sleep 30
    cp /etc/app.conf /var/backups/.app.conf.tmp 2>/dev/null || true
    chmod 644 /var/backups/.app.conf.tmp 2>/dev/null || true
    mv /var/backups/.app.conf.tmp /var/backups/app.conf 2>/dev/null || true
  done
) &

printf '%s\n' \
  '=== OpenRange Training Box ===' \
  'This machine is a simulated lab target. Never reuse lab credentials elsewhere.' \
  'Lab account: learner / learner' \
  'An appwatch agent manages its secrets somewhere under /etc.' \
  > /etc/motd

ssh-keygen -A >/dev/null

exec /usr/sbin/sshd -D -e
