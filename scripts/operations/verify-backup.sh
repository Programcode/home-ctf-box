#!/usr/bin/env bash
# Non-destructive restore proof: spin up a throwaway postgres container,
# restore the backup into it, and compare per-table row counts against the
# manifest.json captured at backup time. Never touches live services.
#
# Usage: scripts/operations/verify-backup.sh [backup-dir]
#
# Environment:
#   VERIFY_KEEP_CONTAINER   1 leaves the temp container running for debugging

set -euo pipefail

LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null # resolved at runtime via LIB_DIR
source "$LIB_DIR/_lib.sh"

ROOT="$(repo_root)"
require_docker
command -v jq >/dev/null 2>&1 || die "jq is required to compare manifest.json"

BACKUP_ROOT="${BACKUP_ROOT:-$ROOT/backups}"
BACKUP="${1:-$(latest_backup_dir "$BACKUP_ROOT")}"
case "$BACKUP" in
  /*) ;;
  *) BACKUP="$ROOT/${BACKUP#./}" ;;
esac
BACKUP="${BACKUP%/}"

[[ -n "$BACKUP" && -d "$BACKUP" ]] || die "no backup directory found"
[[ -f "$BACKUP/postgres.sql.gz" ]] || die "no postgres.sql.gz in $BACKUP"
[[ -f "$BACKUP/manifest.json" ]] || die "no manifest.json in $BACKUP; re-run a current backup.sh"

(cd "$BACKUP" && sha256sum --check --quiet SHA256SUMS) || die "checksum mismatch; backup is corrupt"

VERIFY_IMAGE="${VERIFY_IMAGE:-postgres:16.4-alpine}"
CONTAINER="openrange-backup-verify-$$"
COUNTS_FILE="$(mktemp)"

cleanup() {
  rm -f "$COUNTS_FILE"
  if [[ "${VERIFY_KEEP_CONTAINER:-0}" == "1" ]]; then
    log "keeping $CONTAINER for debugging (remember to docker rm it)"
  else
    docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

log "starting throwaway postgres ($VERIFY_IMAGE) as $CONTAINER"
docker run -d --rm --name "$CONTAINER" \
  -e POSTGRES_USER="$OPENRANGE_DB_USER" \
  -e POSTGRES_PASSWORD=verify-only \
  -e POSTGRES_DB="$OPENRANGE_DB_NAME" \
  "$VERIFY_IMAGE" >/dev/null

log "waiting for postgres to accept connections"
for _ in $(seq 1 30); do
  if docker exec "$CONTAINER" pg_isready -U "$OPENRANGE_DB_USER" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done
docker exec "$CONTAINER" pg_isready -U "$OPENRANGE_DB_USER" >/dev/null ||
  die "temp postgres never became ready"

log "restoring dump into temp container"
gunzip -c "$BACKUP/postgres.sql.gz" |
  docker exec -i "$CONTAINER" psql -qU "$OPENRANGE_DB_USER" -d "$OPENRANGE_DB_NAME"

log "comparing row counts against manifest.json"
OPENRANGE_PG_CONTAINER="$CONTAINER" table_counts >"$COUNTS_FILE"

mismatches=0
compared=0
while IFS='|' read -r schema table expected; do
  [[ -n "$schema" ]] || continue
  actual="$(awk -F'|' -v s="$schema" -v t="$table" '$1 == s && $2 == t {print $3}' "$COUNTS_FILE")"
  if [[ -z "$actual" ]]; then
    log "MISSING: $schema.$table exists in manifest but not after restore"
    mismatches=$((mismatches + 1))
    continue
  fi
  compared=$((compared + 1))
  if [[ "$actual" != "$expected" ]]; then
    log "MISMATCH: $schema.$table expected=$expected restored=$actual"
    mismatches=$((mismatches + 1))
  fi
done < <(jq -r '.tables[] | "\(.schema)|\(.name)|\(.rows)"' "$BACKUP/manifest.json")

((compared > 0)) || die "no manifest tables were found in the restored database"

if ((mismatches > 0)); then
  die "verification failed with $mismatches mismatch(es) out of $((compared + mismatches)) tables"
fi

ok "verified: all $compared tables match manifest.json"
ok "restore proof passed for $BACKUP"
