#!/bin/sh
# Room entrypoint: drops the flag into the adminsim profile, runs sshd.
set -eu

FLAG="${ROOM_FLAG:-FLAG{FLAGNOTSET0000000000000000}}"

umask 022

# Recreated every boot so the room resets cleanly.
printf '%s\n' 'Administrator-sim workstation. The guarded value lives here.' '' \
  "$FLAG" > /home/adminsim/flag.txt
chown adminsim:adminsim /home/adminsim/flag.txt
chmod 600 /home/adminsim/flag.txt

printf '%s\n' '- finish quarterly plan (see Documents)' \
  '- do not leave autologon enabled on real machines; this lab exists to show why' \
  > /home/adminsim/notes.txt
chown adminsim:adminsim /home/adminsim/notes.txt

hostname_bin="$(command -v hostname || true)"
if [ -n "$hostname_bin" ]; then
  h="$("$hostname_bin")"
  grep -q " $h" /etc/hosts 2>/dev/null || printf '127.0.0.1 %s\n' "$h" >> /etc/hosts
fi

printf '%s\n' \
  '=== OpenRange Training Box ===' \
  'Simulation notice: this Debian container simulates the Windows' \
  'registry with plain-text .hiv files under /opt/registry. No real' \
  'Windows code or hive format is involved. Never reuse lab' \
  'credentials elsewhere.' \
  'Lab account: learner / learner' \
  > /etc/motd

ssh-keygen -A >/dev/null

exec /usr/sbin/sshd -D -e
