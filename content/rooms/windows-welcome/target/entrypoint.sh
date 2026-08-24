#!/bin/sh
# Room entrypoint: rebuilds the simulated C: drive, drops the flag, runs sshd.
set -eu

FLAG="${ROOM_FLAG:-FLAG{FLAGNOTSET0000000000000000}}"

umask 022

# The ~/winfs tree is recreated on every boot so the room resets cleanly.
WINFS=/home/learner/winfs
rm -rf "$WINFS"
mkdir -p \
  "$WINFS/ProgramData/SimLogs" \
  "$WINFS/Windows/System32/drivers/etc" \
  "$WINFS/Users/guest/Downloads" \
  "$WINFS/Users/learner/Documents" \
  "$WINFS/Users/winadmin/Desktop" \
  "$WINFS/Users/winadmin/Documents" \
  "$WINFS/Users/tsvc/Documents"

printf '%s\n' '# Simulated hosts file (stand-in for C:\Windows\System32\drivers\etc\hosts)' \
  '127.0.0.1 localhost WIN-SIM01' > "$WINFS/Windows/System32/drivers/etc/hosts"

printf '%s\n' 'simlog service started' 'license check passed (simulated)' \
  'telemetry endpoint unreachable (expected in simulation)' \
  > "$WINFS/ProgramData/SimLogs/app-log.txt"

printf '%s\n' 'Welcome to WIN-SIM01, guest.' 'Nothing interesting is stored under this profile.' \
  > "$WINFS/Users/guest/Downloads/first-run.txt"

printf '%s\n' 'Getting started on WIN-SIM01' '' \
  'This shell is real PowerShell. Get-Command lists commands,' \
  'Get-Help explains them, Get-ChildItem walks the tree.' \
  > "$WINFS/Users/learner/Documents/getting-started.txt"

printf '%s\n' '- approve printer driver' '- rotate service passwords (done last month)' \
  '- archive old installers' > "$WINFS/Users/winadmin/Desktop/todo.txt"

printf '%s\n' 'Q3 spend: licenses, hardware, coffee (see finance for real numbers).' \
  > "$WINFS/Users/winadmin/Documents/budget-q3.txt"

printf '%s\n' 'IT handover notes, tsvc account' '' \
  'The night shift keeps the guarded token below so handovers do not' \
  'depend on anyone being awake. It is the only value of its kind on' \
  'this box.' '' "$FLAG" > "$WINFS/Users/tsvc/Documents/handover-notes.txt"

chown -R learner:learner "$WINFS"

# Keep sudo-free boxes quiet about unresolvable container hostnames.
hostname_bin="$(command -v hostname || true)"
if [ -n "$hostname_bin" ]; then
  h="$("$hostname_bin")"
  grep -q " $h" /etc/hosts 2>/dev/null || printf '127.0.0.1 %s\n' "$h" >> /etc/hosts
fi

printf '%s\n' \
  '=== OpenRange Training Box ===' \
  'Simulation notice: this is a Debian Linux container presenting a' \
  'simulated Windows environment. PowerShell itself is real; the' \
  'computer name and C: layout are stand-ins. Never reuse lab' \
  'credentials elsewhere.' \
  'Lab account: learner / learner' \
  > /etc/motd

ssh-keygen -A >/dev/null

exec /usr/sbin/sshd -D -e
