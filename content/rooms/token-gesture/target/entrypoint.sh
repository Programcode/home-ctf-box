#!/bin/sh
# Room entrypoint: resets token state, drops the flag, runs sshd.
set -eu

FLAG="${ROOM_FLAG:-FLAG{FLAGNOTSET0000000000000000}}"

umask 022

printf '%s\n' "$FLAG" > /root/flag.txt
chown root:root /root/flag.txt
chmod 600 /root/flag.txt

# Trusted store and cache are recreated on every boot so learner edits
# never survive a reset.
rm -rf /opt/tokens /var/cache/tokentool
mkdir -p /opt/tokens /var/cache/tokentool
cp /usr/local/share/token-gesture/tokens/*.json /opt/tokens/
cp /usr/local/share/token-gesture/tokens/README.txt /opt/tokens/
chmod 777 /var/cache/tokentool

hostname_bin="$(command -v hostname || true)"
if [ -n "$hostname_bin" ]; then
  h="$("$hostname_bin")"
  grep -q " $h" /etc/hosts 2>/dev/null || printf '127.0.0.1 %s\n' "$h" >> /etc/hosts
fi

printf '%s\n' \
  '=== OpenRange Training Box ===' \
  'Simulation notice: this Debian container simulates Windows token' \
  'concepts with JSON files under /opt/tokens and a helper called' \
  'tokentool. No Windows kernel, handle table, or privilege exists' \
  'here; see /opt/tokens/README.txt for what each field stands in for.' \
  'Never reuse lab credentials elsewhere.' \
  'Lab account: learner / learner (sudo grant: tokentool only)' \
  > /etc/motd

ssh-keygen -A >/dev/null

exec /usr/sbin/sshd -D -e
