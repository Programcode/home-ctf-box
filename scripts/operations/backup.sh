#!/usr/bin/env bash
# Consistent backup: pg_dump + content/ archive + manifest with exact row
# counts, checksums, optional rclone offload, and local retention pruning.
#
# Usage: scripts/operations/backup.sh [destination-dir]
#
# Environment:
#   OPENRANGE_PG_CONTAINER  dump from this docker container instead of the
#                           compose postgres service (used by tests)
#   OPENRANGE_DB_USER / OPENRANGE_DB_NAME  defaults: openrange / openrange
#   BACKUP_ROOT             default <repo>/backups
#   RETENTION_DAYS          prune stamp dirs older than this (default 14, 0 = keep all)
#   RCLONE_REMOTE           e.g. "gdrive:openrange-backups" - copies the new
#                           backup dir there when set and rclone is installed

set -euo pipefail

LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null # resolved at runtime via LIB_DIR
source "$LIB_DIR/_lib.sh"

ROOT="$(repo_root)"
require_compose_context
command -v jq >/dev/null 2>&1 || die "jq is required to build manifest.json"

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP_ROOT="${BACKUP_ROOT:-$ROOT/backups}"
DEST="${1:-$BACKUP_ROOT/$STAMP}"

mkdir -p "$DEST"
chmod 700 "$DEST"

log "checking database connectivity"
pg_exec -t -c "SELECT 'ok'" | grep -q ok || die "cannot reach postgres (compose up first or set OPENRANGE_PG_CONTAINER)"

log "dumping postgres to $DEST/postgres.sql.gz"
pg_dump_to "$DEST/postgres.sql.tmp"
gzip -9 "$DEST/postgres.sql.tmp"
mv "$DEST/postgres.sql.tmp.gz" "$DEST/postgres.sql.gz"

if [[ -d "$ROOT/content" ]]; then
  log "archiving content/"
  tar czf "$DEST/content.tgz" --exclude='__pycache__' --exclude='*.pyc' -C "$ROOT" content
else
  log "no content/ directory at $ROOT; skipping content archive"
fi

log "capturing row counts into manifest.json"
{
  printf '{\n'
  printf '  "created_utc": "%s",\n' "$STAMP"
  if [[ -n "${OPENRANGE_PG_CONTAINER:-}" ]]; then
    printf '  "source": {"kind": "container", "name": "%s"},\n' "$OPENRANGE_PG_CONTAINER"
  else
    printf '  "source": {"kind": "compose", "service": "%s"},\n' "$OPENRANGE_PG_SERVICE"
  fi
  printf '  "database": "%s",\n' "$OPENRANGE_DB_NAME"
  printf '  "tables": [\n'
  first=1
  while IFS='|' read -r schema table rows; do
    [[ -n "$schema" ]] || continue
    ((first)) && first=0 || printf ',\n'
    printf '    {"schema": "%s", "name": "%s", "rows": %s}' "$schema" "$table" "$rows"
  done < <(table_counts)
  printf '\n  ]\n}\n'
} >"$DEST/manifest.json"

(
  cd "$DEST"
  find . -maxdepth 1 -type f \( -name '*.gz' -o -name '*.json' \) -printf '%f\n' | LC_ALL=C sort |
    xargs sha256sum >SHA256SUMS
)

log "verifying freshly written backup"
(cd "$DEST" && sha256sum --check --quiet SHA256SUMS) || die "fresh backup failed its own checksum verification"

TABLE_COUNT="$(jq '.tables | length' "$DEST/manifest.json")"
TOTAL_ROWS="$(jq '[.tables[].rows] | add' "$DEST/manifest.json")"

if [[ -n "${RCLONE_REMOTE:-}" ]]; then
  if command -v rclone >/dev/null 2>&1; then
    log "copying backup to rclone remote $RCLONE_REMOTE/openrange/$STAMP"
    rclone copy "$DEST" "$RCLONE_REMOTE/openrange/$STAMP"
  else
    log "RCLONE_REMOTE is set but rclone is not installed; skipping upload"
  fi
fi

RETENTION_DAYS="${RETENTION_DAYS:-14}"
if ((RETENTION_DAYS > 0)); then
  pruned="$(find "$BACKUP_ROOT" -mindepth 1 -maxdepth 1 -type d -name '*[0-9]*Z' -mtime "+$RETENTION_DAYS" -print -exec rm -rf {} + 2>/dev/null | wc -l)"
  if ((pruned > 0)); then
    log "retention: removed $pruned backup dir(s) older than $RETENTION_DAYS days"
  fi
fi

ok "backup complete: $DEST ($TABLE_COUNT tables, $TOTAL_ROWS rows)"
du -sh "$DEST" | awk '{print "[+] size:", $1}'
