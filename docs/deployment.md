# Deploying OpenRange

Production packaging for the single-node Community Edition: three
multi-stage images, one Compose stack, Caddy edge with automatic HTTPS.

- Stack definition: `infra/compose/production.yml`
- Edge proxy config: `infra/caddy/Caddyfile`
- Images: `docker/Dockerfile.api`, `docker/Dockerfile.web`, `docker/Dockerfile.gateway`
- Environment template: `.env.example` (commented production block at the bottom)

## Prerequisites

- Linux host, x86_64 or arm64 (Raspberry Pi 5 works for light rooms)
- Docker Engine 24+ with the compose plugin
- 2+ CPUs and 4 GB RAM minimum; see sizing table below
- Ports 8080/8443 free for local trials, or 80/443 for a public domain

## Fresh install

```bash
git clone https://github.com/<owner>/home-ctf-box.git openrange
cd openrange
cp .env.example .env
```

Edit `.env`. Uncomment the production block at the bottom of the file, then fill every secret. Values marked `openssl rand -hex 32` must be generated, not left blank:

```bash
openssl rand -hex 32   # repeat per secret: SECRET_KEY, FLAG_MASTER_KEY,
                       # RUNNER_API_TOKEN, GATEWAY_SECRET, MEILI_MASTER_KEY,
                       # POSTGRES_PASSWORD, S3 keys
```

The typed validator (`packages/config`) fails closed in production mode:
missing secrets or leftover `dev-only` placeholders stop startup instead of
serving traffic.

Bring up databases and caches first, apply schema, then start everything:

```bash
docker compose -f infra/compose/production.yml --env-file .env up -d postgres redis minio meilisearch
docker compose -f infra/compose/production.yml --env-file .env run --rm migrate
docker compose -f infra/compose/production.yml --env-file .env up -d --wait
```

`--wait` returns once every healthcheck passes. The API reports readiness at
`/api/readyz` (database, Redis, content dir, migration head); the gateway at
`/healthz`; the web container answers on `/`.

Smoke test through the Caddy edge (loopback default):

```bash
curl -fsS http://127.0.0.1:8080/api/readyz | jq .
curl -fsS http://127.0.0.1:8080/healthz
curl -fsSI http://127.0.0.1:8080/ | head -n1
```

Create the first admin through the setup wizard at
`http://<host>:8080/setup`; no default credentials ship in any image.

## Upgrading

Pin upgrades to immutable tags; never run `latest` unattended.

```bash
# 1. Backup first (Postgres dump + content archive + manifest)
bash scripts/operations/backup.sh backups/pre-upgrade-$(date -u +%Y%m%d)

# 2. Pull new images
sed -i 's/^OPENRANGE_.*_IMAGE=.*/&/' .env   # set *_IMAGE to the new vX.Y.Z
docker compose -f infra/compose/production.yml --env-file .env pull

# 3. Apply migrations via the one-shot container, then roll services
docker compose -f infra/compose/production.yml --env-file .env up -d postgres redis minio meilisearch
docker compose -f infra/compose/production.yml --env-file .env run --rm migrate
docker compose -f infra/compose/production.yml --env-file .env up -d --wait
```

Repeat the readyz smoke test after each upgrade.

## Rollback

Images are immutable digests; rollback is a tag flip plus restart:

```bash
# point OPENRANGE_*_IMAGE back at the previous vX.Y.Z in .env
docker compose -f infra/compose/production.yml --env-file .env up -d --force-recreate --wait
```

Database caveat: migrations are forward-only here. If a release migrated
the schema, restore the pre-upgrade backup instead of downgrading in place:

```bash
docker compose -f infra/compose/production.yml --env-file .env down
bash scripts/operations/restore.sh backups/<stamp>
# then start the old image set and re-run the smoke test
```

## TLS and DNS

With `OPENRANGE_DOMAIN=` empty the stack serves plain HTTP on loopback,
which is right for trials and for running behind your own reverse proxy.

For public installs: create an A/AAAA record for `range.example.com`
pointing at the host, then set in `.env`:

```text
OPENRANGE_DOMAIN=range.example.com
CADDY_HTTP_BIND=0.0.0.0:80
CADDY_HTTPS_BIND=0.0.0.0:443
OPENRANGE_PUBLIC_URL=https://range.example.com
```

Recreate with `docker compose -f infra/compose/production.yml --env-file .env up -d caddy`.
Caddy obtains and renews the Let's Encrypt certificate automatically;
certificates and ACME state persist in the `caddy-data` volume.

Lab instances themselves must never be exposed publicly; only this control
plane edge is. Lab traffic leaves through the gateway route `/gateway/*`,
and room containers stay on internal networks (see docs/decisions/
0009-deployment-boundaries.md).

## Resource sizing

| Profile     | CPU    | RAM   | Fits                                   |
| ----------- | ------ | ----- | -------------------------------------- |
| Minimum     | 2 vCPU | 4 GB  | Control plane + a few light web rooms  |
| VPS         | 4 vCPU | 8 GB  | Small classes, concurrent browser labs |
| Recommended | 8 vCPU | 16 GB | Full single-node Community Edition     |

Per-service limits are declared in `production.yml` under
`deploy.resources.limits`; scale them together with host capacity.
Windows/AD content and multi-host ranges need external x86_64 runners
registered against the lab runner API instead of the Pi-class host.

## Day-2 notes

- Content updates: edit `content/`, then `docker compose -f infra/compose/production.yml --env-file .env restart api`;
  content is mounted read-only from the checkout, not baked into images.
- Logs rotate at 10 MB x 3 per service (json-file).
- Backups: `scripts/operations/backup.sh` (cron it), verify with
  `scripts/operations/verify-backup.sh`, restore with
  `scripts/operations/restore.sh`.
- Release automation lives in `.github/workflows/release.yml`: pushing tag
  `vX.Y.Z` builds all three images into GHCR and attaches syft SPDX SBOMs
  plus a changelog to the GitHub Release.
