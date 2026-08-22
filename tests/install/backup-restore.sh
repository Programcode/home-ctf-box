#!/usr/bin/env bash
# Backup/restore proof: write a sentinel into Postgres, back up, drop
# the data, restore, and confirm the sentinel came back.
set -euo pipefail

cd "$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

docker compose --profile core up -d --wait >/dev/null
psql() { docker compose exec -T postgres psql -qAtU openrange openrange -c "$1"; }

SENTINEL="restore-proof-$(date +%s)"
psql "CREATE TABLE IF NOT EXISTS restore_proof (k text primary key, v text)" >/dev/null
psql "INSERT INTO restore_proof VALUES ('sentinel', '$SENTINEL') ON CONFLICT (k) DO UPDATE SET v = excluded.v" >/dev/null

echo "[*] running backup"
bash scripts/backup.sh >/dev/null
BACKUP="$(ls -1d backups/*/ | sort | tail -1)"

psql "DELETE FROM restore_proof" >/dev/null
[[ "$(psql "SELECT count(*) FROM restore_proof")" == "0" ]]

echo "[*] restoring from $BACKUP"
OPENRANGE_ASSUME_YES=1 bash scripts/restore.sh "$BACKUP" >/dev/null 2>&1 || \
  OPENRANGE_ASSUME_YES=1 bash scripts/restore.sh "$BACKUP"

GOT="$(psql "SELECT v FROM restore_proof WHERE k = 'sentinel'")"
if [[ "$GOT" != "$SENTINEL" ]]; then
  echo "FAIL: expected $SENTINEL after restore, got: ${GOT:-<empty>}"
  exit 1
fi

echo "[PASS] backup/restore proof round-trips ($BACKUP)"
