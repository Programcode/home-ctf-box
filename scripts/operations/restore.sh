#!/usr/bin/env bash
# Restore a backup made by scripts/operations/backup.sh.
#
# Default target is the running compose postgres: this DROPS the openrange
# database and overwrites the extracted content directory. Two guards:
# checksums are verified first, and an interactive prompt requires typing
# RESTORE (skipped with OPENRANGE_ASSUME_YES=1).
#
# Usage: scripts/operations/restore.sh [backup-dir]
#
# Environment:
#   OPENRANGE_ASSUME_YES    1 skips the destructive prompt
#   OPENRANGE_PG_CONTAINER  restore into this container instead of compose;
#                           used by verification flows, never touches live data
#   CONTENT_TARGET          where content.tgz extracts (default <repo>/content)

set -euo pipefail

LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null # resolved at runtime via LIB_DIR
source "$LIB_DIR/_lib.sh"

ROOT="$(repo_root)"
require_compose_context

BACKUP_ROOT="${BACKUP_ROOT:-$ROOT/backups}"
BACKUP="${1:-$(latest_backup_dir "$BACKUP_ROOT")}"
case "$BACKUP" in
  /*) ;;
  *) BACKUP="$ROOT/${BACKUP#./}" ;;
esac
BACKUP="${BACKUP%/}"

[[ -n "$BACKUP" && -d "$BACKUP" ]] || die "no backup directory found (pass one, e.g. backups/<stamp>)"
[[ -f "$BACKUP/postgres.sql.gz" ]] || die "no postgres.sql.gz in $BACKUP"

if [[ -f "$BACKUP/SHA256SUMS" ]]; then
  log "verifying backup checksums"
  (cd "$BACKUP" && sha256sum --check --quiet SHA256SUMS) || die "checksum mismatch; refusing to restore a corrupt backup"
else
  log "no SHA256SUMS in $BACKUP; continuing without integrity proof"
fi

if [[ -n "${OPENRANGE_PG_CONTAINER:-}" ]]; then
  log "target: container $OPENRANGE_PG_CONTAINER (non-destructive to the compose stack)"
else
  log "target: compose service '$OPENRANGE_PG_SERVICE' database '$OPENRANGE_DB_NAME'"
fi

if [[ "${OPENRANGE_ASSUME_YES:-0}" != "1" ]]; then
  if [[ -f "$BACKUP/content.tgz" && -z "${OPENRANGE_PG_CONTAINER:-}" ]]; then
    printf '[!] this drops the target database and overwrites %s\n' "${CONTENT_TARGET:-$ROOT/content}"
  else
    printf '[!] this drops the target database\n'
  fi
  read -r -p "type RESTORE to continue: " answer
  [[ "$answer" == "RESTORE" ]] || { log "aborted"; exit 1; }
fi

log "restoring database from $(basename "$BACKUP")"
pg_exec -q -c "DROP SCHEMA public CASCADE" >/dev/null
pg_exec -q -c "CREATE SCHEMA public" >/dev/null
gunzip -c "$BACKUP/postgres.sql.gz" | pg_exec -q

RESTORED_TABLES="$(pg_exec -t -c "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE'")"
ok "database restored ($RESTORED_TABLES tables)"

if [[ -f "$BACKUP/content.tgz" ]]; then
  CONTENT_TARGET="${CONTENT_TARGET:-$ROOT/content}"
  log "extracting content archive into $CONTENT_TARGET"
  mkdir -p "$CONTENT_TARGET"
  tar xzf "$BACKUP/content.tgz" -C "$CONTENT_TARGET" --strip-components=1
  ok "content restored"
fi

ok "restore complete from $BACKUP"
