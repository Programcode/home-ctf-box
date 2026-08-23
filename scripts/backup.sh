#!/usr/bin/env bash
# Dump Postgres and archive the object-storage volume into
# backups/<timestamp>/. Stop writes for a consistent snapshot in
# production (maintenance mode) before running this.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
DEST="${1:-$ROOT/backups/$STAMP}"
mkdir -p "$DEST"
chmod 700 "$DEST"

echo "[*] dumping postgres to $DEST/postgres.sql.gz"
docker compose exec -T postgres pg_dump -U openrange openrange | gzip >"$DEST/postgres.sql.gz"

MINIO_CID="$(docker compose ps -q minio || true)"
if [[ -n "$MINIO_CID" ]]; then
  MINIO_VOL="$(docker inspect -f '{{range .Mounts}}{{if eq .Destination "/data"}}{{.Name}}{{end}}{{end}}' "$MINIO_CID")"
  if [[ -n "$MINIO_VOL" ]]; then
    echo "[*] archiving object-storage volume $MINIO_VOL"
    docker run --rm \
      -v "$MINIO_VOL":/src:ro \
      -v "$DEST":/dest \
      alpine:3.20 tar czf /dest/minio-data.tgz -C /src .
  fi
fi

(
  cd "$DEST"
  find . -maxdepth 1 \( -name '*.gz' -o -name '*.tgz' \) -printf '%f\n' | sort | xargs sha256sum > SHA256SUMS
)

echo "[*] verifying checksums of the fresh backup"
( cd "$DEST" && sha256sum --check --quiet SHA256SUMS ) || {
  echo "FAIL: freshly written backup failed checksum verification" >&2
  exit 1
}

echo "[+] backup complete: $DEST"
ls -la "$DEST"
