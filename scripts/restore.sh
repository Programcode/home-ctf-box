#!/usr/bin/env bash
# Restore the newest (or given) backup directory into the running stack.
# Destructive: wipes the postgres database and object storage first.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP="${1:-$(ls -1d "$ROOT"/backups/*/ 2>/dev/null | sort | tail -1)}"
case "$BACKUP" in
  /*) ;;
  *) BACKUP="$ROOT/${BACKUP#./}" ;;
esac
BACKUP="${BACKUP%/}"

if [[ -z "$BACKUP" || ! -f "$BACKUP/postgres.sql.gz" ]]; then
  echo "no backup with postgres.sql.gz found (pass a directory, e.g. make restore BACKUP=backups/<stamp>)" >&2
  exit 1
fi

echo "[!] this drops the openrange database and minio objects from $BACKUP"
if [[ "${OPENRANGE_ASSUME_YES:-0}" != "1" ]]; then
  read -r -p "type RESTORE to continue: " answer
  if [[ "$answer" != "RESTORE" ]]; then
    echo "aborted"
    exit 1
  fi
fi

docker compose exec -T postgres dropdb --if-exists -U openrange openrange
docker compose exec -T postgres createdb -U openrange openrange
gunzip -c "$BACKUP/postgres.sql.gz" | docker compose exec -T postgres psql -q -U openrange openrange

if [[ -f "$BACKUP/minio-data.tgz" ]]; then
  MINIO_CID="$(docker compose ps -q minio || true)"
  if [[ -n "$MINIO_CID" ]]; then
    echo "[*] restoring object-storage volume"
    docker compose stop minio >/dev/null
    MINIO_VOL="$(docker inspect -f '{{range .Mounts}}{{if eq .Destination "/data"}}{{.Name}}{{end}}{{end}}' "$MINIO_CID")"
    docker run --rm \
      -v "$MINIO_VOL":/dst \
      -v "$BACKUP":/src:ro \
      alpine:3.20 sh -c "rm -rf /dst/* /dst/..?* /dst/.[!.]* ; tar xzf /src/minio-data.tgz -C /dst"
    docker compose start minio >/dev/null
  fi
fi

echo "[+] restore complete; run smoke checks before serving traffic"
