#!/bin/sh
# Room entrypoint: rebuilds share contents, starts smbd and the HTTP mirror.
set -eu

FLAG="${ROOM_FLAG:-FLAG{FLAGNOTSET0000000000000000}}"

umask 027

# Share contents are recreated on every boot so the room resets cleanly.
rm -rf /srv/samba
mkdir -p /srv/samba/public /srv/samba/dev$

printf '%s\n' 'Welcome to the SIMFILE01 public drop zone.' \
  'This share is browseable by anyone on the training network.' \
  'House rule: nothing sensitive goes in here, use team shares for that.' \
  > /srv/samba/public/welcome.txt

printf '%s\n' 'Weekly ops sync, summary notes' '' \
  '- printer firmware update went fine' \
  '- dev team reminds everyone: their working share is hidden as' \
  '  \\SIMFILE01\dev$ (browse lists will not show it)' \
  '- dev$ login stays on their service account:' \
  '  user smbuser pass SpringSim26 (keep it out of tickets)' \
  '- reminder that hidden does not mean protected; see security wiki' \
  > /srv/samba/public/meeting-notes.txt

printf '%s\n' 'Parking: visitor spots 1-6, loading dock before 8am only.' \
  > /srv/samba/public/facilities.txt

printf '%s\n' 'Deploy notes (dev share)' '' \
  'Staging cutover checklist lives here so it survives laptop swaps.' \
  'The release verification token for this environment is below;' \
  'treat it like the share it sits on.' '' "$FLAG" \
  > /srv/samba/dev$/deploy-notes.txt

printf '%s\n' 'Migration window moved to Friday 22:00 UTC.' \
  > /srv/samba/dev$/db-migration.txt

chown -R root:sharegrp /srv/samba
find /srv/samba -type d -exec chmod 750 {} +
find /srv/samba -type f -exec chmod 640 {} +

/usr/sbin/smbd -D

# The HTTP mirror keeps the container alive; its log captures tracebacks.
python3 /opt/shareweb/app.py >> /var/log/samba/share-mirror.log 2>&1 &
APP_PID=$!
wait "$APP_PID"
