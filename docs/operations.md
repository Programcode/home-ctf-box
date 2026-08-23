# Operations runbook

Observability and backup tooling for the OpenRange control plane
(plan phase 13 core). Everything here runs locally with the compose
stack; no cloud dependencies.

## Quick start

```bash
docker compose --profile core up -d --wait
docker compose -f infra/compose/observability.yml up -d
# Prometheus  http://127.0.0.1:19090
# Grafana     http://127.0.0.1:13000 (admin/admin, dev default)
```

Grafana provisions the `OpenRange API overview` dashboard and the
Prometheus/Loki datasources automatically from
`infra/observability/grafana/provisioning/`.

## Health and readiness endpoints

### GET /api/healthz

Static liveness probe. Returns `{"status": "ok"}` without touching any
dependency. Load balancers should use it to decide process restarts;
it never reports partial degradation.

### GET /api/readyz

Deep readiness probe. Runs four component checks and returns 200 only
when the process can serve real traffic; otherwise 503.

| Check         | Passes when                                                                         | Failure policy                                                                                   |
| ------------- | ----------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| `database`    | `SELECT 1` succeeds on the pooled engine                                            | fail closed                                                                                      |
| `redis`       | `PING` succeeds within 2 s (shared rate-limit client)                               | fail closed                                                                                      |
| `content_dir` | content root (`CONTENT_DIR`, default `./content`) exists and is readable            | fail closed                                                                                      |
| `migrations`  | rows in `alembic_version` equal the head revision(s) of `apps/api/alembic/versions` | fail closed on mismatch; fail open with a note when Alembic sources are absent (packaged images) |

Response body lists each check so operators see which dependency is
unhappy:

```json
{
  "status": "ready",
  "checks": {
    "database": { "ok": true },
    "redis": { "ok": true },
    "content_dir": { "ok": true, "detail": "./content" },
    "migrations": { "ok": true, "head": ["b7d4e2a91c63"], "applied": ["b7d4e2a91c63"] }
  }
}
```

Note: the deep `/api/readyz` is registered before the legacy shallow
route from `apps/api/src/openrange/api/health.py` and therefore shadows
it. The legacy module stays untouched; removing the duplicate route is
left to a future cleanup that owns that file.

## GET /api/metrics

Prometheus text format (`text/plain; version=0.0.4`). Scraped by the
`openrange-api` job in `infra/observability/prometheus.yml`.

Families:

- `openrange_process_uptime_seconds` gauge
- `openrange_gc_collections_total{generation}` counter (CPython gc stats)
- `openrange_db_pool_size`, `openrange_db_pool_checked_out` gauges (SQLAlchemy pool)
- `openrange_http_requests_total{method,path,status}` counter
- `openrange_http_request_duration_seconds_sum/_count{method,path}` counters
- `openrange_lab_instances{state}` gauge (omitted entirely when the labs
  models or database are unavailable)

Latency histograms are not exposed yet, so p95 is not computable; the
dashboard shows the average until buckets land in a later phase.

### Why unauthenticated is safe here

1. No user data: labels contain methods, route templates, status codes,
   and aggregate counts only. There are no ids, emails, tokens, or paths
   echoed back verbatim.
2. Bounded cardinality: at most 200 distinct path-template labels exist;
   anything beyond collapses into one `_overflow` series. Unmatched
   requests (scanner noise, 404s without a route) share the single
   `unmatched` label.
3. Rate limited: the endpoint reuses the shared sliding-window limiter
   (60 scrapes/min per client). Like the auth limiter it fails open when
   Redis is down so observability never breaks availability.
4. Network posture: the compose stack binds every port to 127.0.0.1.
   Expose metrics publicly only behind an authenticated proxy.

The middleware skips `/api/metrics` itself so scraping does not inflate
its own counters.

## Structured logging

Audit finding (phase 13): request correlation exists today but JSON log
emission does not yet. `RequestContextMiddleware`
(`apps/api/src/openrange/api/middleware.py`) assigns a request id per
request, accepts an incoming `x-request-id`, echoes it back as a
response header, and stores it on `request.state.request_id`. Nothing
currently writes it into a log line, and uvicorn's access logs are plain
text. Closing that gap means touching middleware/logging setup outside
this branch's ownership boundary; treat it as the first item of the next
observability increment.

Field contract for the future JSON emitter (and for anything parsing
logs today):

- `request_id`: hex string, propagated via `x-request-id` header
- `method`, `path_template`, `status`: same values as the metric labels
- `duration_ms`: float
- `logger`, `level`, `message`, `timestamp`: standard Python logging fields
- never logged: passwords, cookies, tokens, flag material

### Shipping logs with Promtail

`infra/compose/observability.yml` runs Loki plus Promtail configured for
docker service discovery (`infra/observability/promtail-config.yml`).
Only containers labeled `logging=promtail` are scraped:

```yaml
services:
  api:
    # ...
    labels:
      logging: promtail
    logging:
      driver: json-file
      options:
        max-size: '10m'
        max-file: '3'
```

Promtail unwraps the json-file envelope (`log`/`stream`/`time`) and keeps
stdout/stderr as a label. Until the api emits JSON lines, Grafana's Loki
Explore shows uvicorn access-log text lines; once the emitter above
lands, parse them with LogQL `| json` without changing Promtail config.

Set rotation limits either per service as above or globally in
`/etc/docker/daemon.json`; without them the host disk is the retention
policy, which is not a policy.

## Backup, restore, verify

Scripts live in `scripts/operations/` and share `_lib.sh`.

```bash
bash scripts/operations/backup.sh                 # backups/<UTC stamp>/
bash scripts/operations/verify-backup.sh          # temp-container restore proof
OPENRANGE_ASSUME_YES=1 bash scripts/operations/restore.sh backups/<stamp>
```

What backup produces per stamp directory:

- `postgres.sql.gz`: plain SQL dump via `pg_dump` inside the running
  compose postgres container
- `content.tgz`: the repo `content/` directory (rooms, bundles, solvers)
- `manifest.json`: creation time, source target, and exact row count per
  public table at backup time
- `SHA256SUMS`: checksums over the payload files

Environment knobs:

- `BACKUP_ROOT` (default `<repo>/backups`)
- `RETENTION_DAYS` (default 14, `0` disables pruning of old stamp dirs)
- `RCLONE_REMOTE` (e.g. `b2:openrange`): copies the new backup there when
  set and `rclone` is installed; skipped silently otherwise
- `OPENRANGE_PG_CONTAINER`: point dump/restore at an arbitrary container
  instead of the compose postgres service; used by tests and verification
- `CONTENT_TARGET` (restore only): extraction directory, default
  `<repo>/content`
- `VERIFY_KEEP_CONTAINER=1`: keep the verify container around for debugging

`verify-backup.sh` starts a throwaway `postgres:16.4-alpine`, restores
the dump, and diffs every manifest row count against the restored
tables. It never touches live services and removes its container on exit.

`restore.sh` drops and recreates the `public` schema in the target
database and re-extracts `content.tgz`. It verifies checksums before
touching anything and requires typing `RESTORE` unless
`OPENRANGE_ASSUME_YES=1`. Stop writes (maintenance mode) before restoring
in shared environments.

### RPO/RTO (local stack, phase 13 baseline)

- RPO: bounded by backup cadence. The scripts are cron-friendly; hourly
  runs give a 1 h RPO. Offsite copy via `RCLONE_REMOTE` protects against
  host loss.
- RTO: restore into a fresh stack takes minutes: `verify-backup.sh`
  demonstrates the mechanical path end-to-end. Plan gate calls for a
  restore proof each release; run `make test-backup-restore` or the
  three scripts above as that proof.

## Known gaps versus full phase 13

- Traces (OpenTelemetry), alert rules, queue-depth and gateway panels:
  later increments of this phase.
- p95 latency needs histogram buckets; average only today.
- JSON log emission gap described under Structured logging.
