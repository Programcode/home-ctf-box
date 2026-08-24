#!/bin/sh
# Room entrypoint: resets service state, starts the 30-second root loop, runs sshd.
set -eu

FLAG="${ROOM_FLAG:-FLAG{FLAGNOTSET0000000000000000}}"

umask 022
printf '%s\n' "$FLAG" > /root/flag.txt
chmod 600 /root/flag.txt

# The updater payload is rewritten on every boot so learner edits never
# survive a reset.
cat > /opt/services/updater/bin/uhelper.sh <<'EOF'
#!/bin/sh
echo "$(date +%FT%T) uhelper heartbeat"
EOF
chown root:learners /opt/services/updater/bin/uhelper.sh
chmod 775 /opt/services/updater/bin/uhelper.sh

rm -f /tmp/flag.out
rm -f /var/log/services-sim.log

(
  while :; do
    /usr/local/sbin/service-runner.sh >> /var/log/services-sim.log 2>&1 || true
    sleep 30
  done
) &

# Keep sudo-free boxes quiet about unresolvable container hostnames.
hostname_bin="$(command -v hostname || true)"
if [ -n "$hostname_bin" ]; then
  h="$("$hostname_bin")"
  grep -q " $h" /etc/hosts 2>/dev/null || printf '127.0.0.1 %s\n' "$h" >> /etc/hosts
fi

printf '%s\n' \
  '=== OpenRange Training Box ===' \
  'Simulation notice: this Debian container simulates Windows service' \
  'abuse mechanics. The JSON database stands in for SCM registry data;' \
  'a root shell loop stands in for the Service Control Manager.' \
  'Never reuse lab credentials elsewhere.' \
  'Lab account: learner / learner' \
  > /etc/motd

ssh-keygen -A >/dev/null

exec /usr/sbin/sshd -D -e
