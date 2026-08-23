#!/usr/bin/env bash
# Shared helpers for scripts/operations/*.sh.

set -euo pipefail

OPENRANGE_DB_USER="${OPENRANGE_DB_USER:-openrange}"
OPENRANGE_DB_NAME="${OPENRANGE_DB_NAME:-openrange}"
OPENRANGE_PG_SERVICE="${OPENRANGE_PG_SERVICE:-postgres}"

log() { printf '[*] %s\n' "$*"; }
ok() { printf '[+] %s\n' "$*"; }
die() { printf 'FAIL: %s\n' "$*" >&2; exit 1; }

repo_root() {
  (cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
}

# Route every database call through one place so restore/verify can be
# pointed at a throwaway container instead of the compose service.
pg_exec() {
  if [[ -n "${OPENRANGE_PG_CONTAINER:-}" ]]; then
    docker exec -i "$OPENRANGE_PG_CONTAINER" psql -qAtU "$OPENRANGE_DB_USER" -d "$OPENRANGE_DB_NAME" "$@"
  else
    docker compose exec -T "$OPENRANGE_PG_SERVICE" psql -qAtU "$OPENRANGE_DB_USER" -d "$OPENRANGE_DB_NAME" "$@"
  fi
}

pg_dump_to() {
  local target="$1"
  if [[ -n "${OPENRANGE_PG_CONTAINER:-}" ]]; then
    docker exec -i "$OPENRANGE_PG_CONTAINER" pg_dump -U "$OPENRANGE_DB_USER" "$OPENRANGE_DB_NAME" >"$target"
  else
    docker compose exec -T "$OPENRANGE_PG_SERVICE" pg_dump -U "$OPENRANGE_DB_USER" "$OPENRANGE_DB_NAME" >"$target"
  fi
}

require_docker() {
  command -v docker >/dev/null 2>&1 || die "docker CLI not found"
}

require_compose_context() {
  [[ -n "${OPENRANGE_PG_CONTAINER:-}" ]] && return 0
  require_docker
  docker compose version >/dev/null 2>&1 || die "docker compose plugin not available"
}

# Exact per-table row counts as TSV: schema<TAB>table<TAB>rows
table_counts() {
  pg_exec -t -c "SELECT table_schema, table_name FROM information_schema.tables
                 WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
                 ORDER BY table_name" |
    while IFS='|' read -r schema table; do
      [[ -n "$schema" && -n "$table" ]] || continue
      # </dev/null keeps the nested psql from swallowing the listing on stdin
      count="$(pg_exec -t -c "SELECT count(*) FROM \"${schema}\".\"${table}\"" </dev/null | tr -d '[:space:]')"
      printf '%s|%s|%s\n' "$schema" "$table" "$count"
    done
}

latest_backup_dir() {
  local backup_root="$1"
  find "$backup_root" -mindepth 1 -maxdepth 1 -type d -name '*[0-9]*Z' -print 2>/dev/null |
    LC_ALL=C sort -r | head -1
}
