#!/bin/sh
# Room entrypoint: drops the root flag, records exploit conditions, runs sshd.
set -eu

FLAG="${ROOM_FLAG:-FLAG{FLAGNOTSET0000000000000000}}"

umask 022
printf '%s\n' "$FLAG" > /root/flag.txt
chmod 600 /root/flag.txt

printf '%s\n' '5.4.0-42-generic' > /opt/exploit-sim/conditions/kernel_version
printf '%s\n' '1' > /opt/exploit-sim/conditions/ebpf_available
printf '%s\n' '1' > /opt/exploit-sim/conditions/unprivileged_bpf
chown -R root:root /opt/exploit-sim

python3 /usr/local/lib/sysinfo_server.py >/var/log/sysinfo.log 2>&1 &

printf '%s\n' \
  '=== OpenRange Training Box ===' \
  'This machine is a simulated lab target. Never reuse lab credentials elsewhere.' \
  'Lab account: learner / learner' \
  'Appliance slice sysinfo: http (port 8000), path /api/sysinfo' \
  > /etc/motd

ssh-keygen -A >/dev/null

exec /usr/sbin/sshd -D -e
