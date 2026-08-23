#!/bin/sh
# Room entrypoint: prepares the box (container + simulated host) and runs sshd.
set -eu

FLAG="${ROOM_FLAG:-FLAG{FLAGNOTSET0000000000000000}}"

umask 022
printf '%s\n' "$FLAG" > /root/flag.txt
chmod 600 /root/flag.txt
# The same flag lives on the simulated host; the inspection tool is its only reader.
printf '%s\n' "$FLAG" > /hostsim/root/flag.txt
chown root:root /hostsim/root/flag.txt
chmod 600 /hostsim/root/flag.txt

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
  '' \
  'Note: this lab box is itself a container. It simulates a host attachment' \
  'under /hostsim; there is no real host and no docker socket here.' \
  > /etc/motd

ssh-keygen -A >/dev/null

exec /usr/sbin/sshd -D -e
