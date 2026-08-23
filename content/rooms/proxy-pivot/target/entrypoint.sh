#!/bin/sh
# Room entrypoint: loopback admin console plus the SSH server.
set -eu

umask 022

# Keep sudo/sshd from warning about an unresolvable container hostname.
hostname_bin="$(command -v hostname || true)"
if [ -n "$hostname_bin" ]; then
  h="$("$hostname_bin")"
  grep -q " $h" /etc/hosts 2>/dev/null || printf '127.0.0.1 %s\n' "$h" >> /etc/hosts
fi

printf '%s\n' \
  '=== OpenRange Training Box ===' \
  'This machine is a simulated lab target. Never reuse lab credentials elsewhere.' \
  'Lab account: learner / learner' \
  'Internal admin console: http://127.0.0.1:9001/admin (loopback only).' \
  > /etc/motd

python3 /usr/local/bin/admin_app.py >/var/log/admin-app.log 2>&1 &

ssh-keygen -A >/dev/null

exec /usr/sbin/sshd -D -e
