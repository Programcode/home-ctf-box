#!/bin/sh
# Room entrypoint: plants the four persistence artifacts (all inert),
# starts the local report endpoint and the harmless heartbeat loop, runs sshd.
set -eu

FLAG="${ROOM_FLAG:-FLAG{FLAGNOTSET0000000000000000}}"

umask 022

# Artifact 3: rogue "monitoring" loop script. Local log appends only.
cat > /usr/local/sbin/sysmon-helper <<'EOF'
#!/bin/sh
# system monitoring helper (do not remove)
while true; do
  echo "$(date -u +%FT%TZ) heartbeat ok" >> /tmp/.beacon.log
  sleep 60
done
EOF
chown root:root /usr/local/sbin/sysmon-helper
chmod 755 /usr/local/sbin/sysmon-helper

# Artifact 1: cron drop-in. No cron daemon is installed, so it never runs.
cat > /etc/cron.d/system-sync <<'EOF'
# keeps system stats in sync (do not remove)
*/5 * * * * root /usr/local/sbin/sysmon-helper >/dev/null 2>&1
EOF
chown root:root /etc/cron.d/system-sync
chmod 644 /etc/cron.d/system-sync

# Artifact 2: modified shell init for the deploy account.
mkdir -p /home/deploy
cat > /home/deploy/.bashrc <<'EOF'
# deploy shell init
[ -z "$PS1" ] && return 0
(sleep 45; echo "$(date -u +%FT%TZ) beacon-ok" >> /tmp/.beacon.log) &
EOF
chown deploy:deploy /home/deploy/.bashrc
chmod 644 /home/deploy/.bashrc
chown deploy:deploy /home/deploy

# Artifact 4: custom systemd unit. No init runs in the container.
cat > /etc/systemd/system/sysmon.service <<'EOF'
[Unit]
Description=System Monitoring Helper

[Service]
ExecStart=/usr/local/sbin/sysmon-helper
Restart=always

[Install]
WantedBy=multi-user.target
EOF
chown root:root /etc/systemd/system/sysmon.service
chmod 644 /etc/systemd/system/sysmon.service

# The helper loop is running (it only prints to the local log), which gives
# analysts a live process and log evidence to correlate with the artifacts.
nohup /usr/local/sbin/sysmon-helper >/dev/null 2>&1 &

python3 /usr/local/lib/report_server.py >/var/log/report-server.log 2>&1 &

printf '%s\n' \
  '=== OpenRange Training Box ===' \
  'This machine is a simulated lab target. Never reuse lab credentials elsewhere.' \
  'Lab account: analyst / analyst' \
  '' \
  'Incident exercise: this host shows signs of an unauthorized presence.' \
  'File verified findings to http://127.0.0.1:8000/api/report (local only).' \
  > /etc/motd

ssh-keygen -A >/dev/null

exec /usr/sbin/sshd -D -e
