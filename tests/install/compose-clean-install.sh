#!/usr/bin/env bash
# Fresh-install proof: from a clean compose project, the documented core
# profile must come up healthy. Leaves the opt-in legacy stack alone.
set -euo pipefail

cd "$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

echo "[*] stopping core/dev services and removing their volumes"
docker compose --profile core --profile dev down -v --remove-orphans >/dev/null 2>&1 || true

echo "[*] starting core profile from scratch"
docker compose --profile core up -d --wait

for svc in postgres redis minio meilisearch; do
  status="$(docker compose ps --format json "$svc" | jq -r '.Health // .State')"
  echo "[*] $svc: $status"
  [[ "$status" == "healthy" ]] || { echo "FAIL: $svc not healthy"; exit 1; }
done

echo "[PASS] clean install: all core services healthy"
