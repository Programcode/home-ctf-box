#!/bin/sh
# Room entrypoint: resets logs and tools, starts responder-sim and checker, runs sshd.
set -eu

# The flag is delivered through the ROOM_FLAG environment variable and
# read by checker.py directly; nothing on disk holds it.

umask 022

# Logs and the public share are recreated on every boot so the room
# resets cleanly.
rm -rf /srv/public /var/log/responder-sim
mkdir -p /srv/public /var/log/responder-sim
chmod 755 /srv/public /var/log/responder-sim

printf '%s\n' \
  'Simulated site inventory, BRANCH-44 (training data)' \
  '' \
  'DC-04        domain controller, DNS authoritative' \
  'PRINTSVR02   print queue, retired last spring' \
  'FILESRV01    legacy file server; several finance workstations' \
  '             still resolve it by bare name because a login script' \
  '             maps \\FILESRV01\finance at sign-in' \
  'AP-Lobby     wireless access point, management VLAN only' \
  > /srv/public/network-inventory.txt
chmod 644 /srv/public/network-inventory.txt

# Learner tooling is refreshed on every boot.
rm -rf /home/learner/tools
mkdir -p /home/learner/tools
cp /usr/local/share/name-resolution/tools/* /home/learner/tools/
chown -R learner:learner /home/learner/tools
chmod 755 /home/learner/tools/namesim_query.py

hostname_bin="$(command -v hostname || true)"
if [ -n "$hostname_bin" ]; then
  h="$("$hostname_bin")"
  grep -q " $h" /etc/hosts 2>/dev/null || printf '127.0.0.1 %s\n' "$h" >> /etc/hosts
fi

python3 /usr/local/bin/responder_sim.py >> /var/log/responder-sim/stdout.log 2>&1 &
python3 /usr/local/bin/checker.py >> /var/log/checker-sim.log 2>&1 &

printf '%s\n' \
  '=== OpenRange Training Box ===' \
  'Simulation notice: this Debian container simulates LLMNR/NBT-NS' \
  'poisoning mechanics with a plain UDP logger on loopback ports' \
  '5355/137 and a fake, clearly labeled credential blob. No real' \
  'protocol bytes or credentials exist here. See' \
  '/home/learner/tools/README.md. Never reuse lab credentials' \
  'elsewhere.' \
  'Lab account: learner / learner' \
  > /etc/motd

ssh-keygen -A >/dev/null

exec /usr/sbin/sshd -D -e
