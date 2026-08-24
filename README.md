# home_ctf_box

A self-hosted cyber range platform (working title: OpenRange) plus a
backwards-compatible 20-room LAN demo. The platform part is a monorepo:
FastAPI control plane, Next.js learner app, lab gateway and runner for
isolated per-user labs, a content SDK, and a growing curriculum of rooms,
paths, and modules. Built for a Raspberry Pi 5 on your home LAN and
developed on an x86 VPS; images are multi-arch.

Status snapshot (2026-08-24): 50 lab-backed rooms across three tracks,
12 learning paths, 36 modules, learning engine, scoring with leaderboards,
orgs and cohorts, notifications, studio review workflow, observability
stack, and CI security gates. Current phase status lives in
`docs/roadmap/implementation-status.md`.

## What runs where

| Piece             | Path                   | What it is                                                                   |
| ----------------- | ---------------------- | ---------------------------------------------------------------------------- |
| Control plane API | `apps/api`             | Auth/RBAC/sessions/MFA, labs, learning, scoring, orgs, notifications, studio |
| Learner web app   | `apps/web`             | Catalog, dashboard, labs, profile pages on Next.js                           |
| Lab gateway       | `apps/lab-gateway`     | Authenticated HTTP proxy to lab targets plus browser SSH terminal            |
| Lab runner        | `apps/lab-runner`      | Per-user container lifecycle with HMAC auth and reconcile loop               |
| Content SDK       | `packages/content-sdk` | Room/path/module schema, linting, solver harness, `cyberrange` CLI           |
| Design system     | `packages/ui`          | Shared tokens and React components                                           |
| Content           | `content/`             | 50 room bundles, 12 paths, 36 modules                                        |
| Compose stacks    | `infra/compose/`       | core, dev, runner, gateway, observability profiles                           |

## Feature list

What actually works today, each verifiable in the linked code:

- Accounts and access: local accounts, session cookies, CSRF, TOTP,
  recovery codes, WebAuthn, optional OIDC, rate limits (`apps/api/src/openrange/api/auth/`).
- Personal labs: start, readiness, extend, reset, stop, expiry reaper,
  cross-tenant isolation at the API layer (`apps/api/src/openrange/api/labs/`).
- Learning engine: enrollment, section progress, catalog queries backing
  the web catalog (`apps/api/src/openrange/api/learning/`).
- Scoring: flag submission with first-blood handling, projections, scoped
  leaderboards including monthly periods (`apps/api/src/openrange/api/scoring/`).
- Organizations: orgs, cohorts, invites, instructor endpoints
  (`apps/api/src/openrange/api/orgs/`).
- Notifications: announcements, preferences, feed, email outbox worker
  (`apps/api/src/openrange/api/notifications/`).
- Studio: drafts, review workflow, atomic publish
  (`apps/api/src/openrange/api/studio/`).
- Observability: Prometheus, Grafana, Loki stack with readiness probes and
  backup/restore tooling (`infra/compose/observability.yml`, `docs/operations.md`).
- Security gates in CI: bandit, pip-audit, pnpm audit, gitleaks
  (`.github/workflows/security.yml`).
- Content quality gate: every bundle passes schema lint plus an automated
  intended-path solver with reset proof on every content PR
  (`.github/workflows/content.yml`).

## Developer quickstart

```sh
make bootstrap   # uv + pnpm toolchains
make check       # ruff, mypy, prettier over everything
make test        # fast unit suite
make up          # postgres :15432, redis :16379, minio :19000, meili :17700
```

Learner web app during development:

```sh
pnpm --filter web dev   # next dev on :3100
```

Content work:

```sh
make test-content   # cyberrange lint over every bundle
make test-solvers   # build room images, run intended-path solvers locally
```

Operations:

```sh
make backup / make restore
docker compose -f infra/compose/observability.yml up -d   # prometheus :19090, grafana :13000
make test-compose-clean-install
make test-backup-restore
```

Targets that do not work yet and exit with an error by design:
`test-contract`, `test-e2e`, `test-a11y`, `test-security`, `test-load`.
The security scans they promise already run directly in
`.github/workflows/security.yml`; the rest are tracked in
`docs/roadmap/implementation-status.md`.

## Legacy LAN demo

The original 20-room scoreboard demo still runs unchanged under the
legacy-v0 compose profile. Same rules as ever: everything binds to
127.0.0.1 unless you say otherwise, never expose it to the internet,
never port-forward it.

```sh
docker compose --profile legacy-v0 up -d --build
```

Platform: http://localhost:8000 (override with `PLATFORM_PORT`). Rooms on
ports 8081 to 8100, one service per room, 2975 points total:

| #   | Room                | Port | Points | Technique                            |
| --- | ------------------- | ---- | ------ | ------------------------------------ |
| 1   | Busted Login        | 8081 | 100    | SQL injection login bypass           |
| 2   | Nosy Files          | 8082 | 150    | Path traversal                       |
| 3   | Ping of Doom        | 8083 | 200    | Shell command injection              |
| 4   | SSTI Greeting       | 8084 | 150    | Jinja server-side template injection |
| 5   | Token Forger        | 8085 | 250    | JWT alg:none forgery                 |
| 6   | IDOR Invoices       | 8086 | 125    | Missing ownership check              |
| 7   | Open Panels         | 8087 | 50     | Exposed debug panel                  |
| 8   | Cookie Shapeshifter | 8088 | 100    | Unsigned base64 cookie forgery       |
| 9   | Regex Doom          | 8089 | 125    | Regex injection                      |
| 10  | Mass Assign         | 8090 | 150    | Blind mass assignment                |
| 11  | XXE Importer        | 8091 | 225    | External entity injection            |
| 12  | Pickle Jar          | 8092 | 275    | Unsafe deserialization RCE           |
| 13  | Trusted Proxy       | 8093 | 75     | X-Forwarded-For spoofing             |
| 14  | Wrong Method        | 8094 | 75     | HTTP verb tampering                  |
| 15  | Open Closet         | 8095 | 50     | Directory listing exposure           |
| 16  | Predictable Reset   | 8096 | 175    | Time-derived reset tokens            |
| 17  | Double Trouble      | 8097 | 150    | HTTP parameter pollution             |
| 18  | Fetch Boy           | 8098 | 200    | SSRF                                 |
| 19  | Union Vault         | 8099 | 225    | UNION-based SQL injection            |
| 20  | Brace Yourself      | 8100 | 125    | Python format string injection       |

Automated full solve from another machine:

```sh
PLATFORM_PORT=8000 ./scripts/demo-solve.sh
```

The script registers a throwaway player, exploits all twenty rooms,
submits the flags, and exits non-zero unless the scoreboard confirms
2975 points.

Full rebuild of the demo from scratch:

```sh
make reset-demo
```

## Deploying to the Pi

```sh
git clone <this repo> && cd home-ctf-box
CTF_BIND=0.0.0.0 docker compose --profile legacy-v0 up -d --build
```

Then browse to `http://<pi-ip>:8000` from your laptop.

## Safety

- Every published port binds to `127.0.0.1` by default (`CTF_BIND`).
- These services are vulnerable **on purpose**. Never expose them to the internet,
  never port-forward them on your router, never run them on a shared host.
- To play from another device on your LAN, set `CTF_BIND=0.0.0.0` in `.env`
  (or export it) only on a trusted home network.
- Lab isolation is enforced by default-deny internal networks created by the
  runner; see `security/threat-model.md`.

## Adding content

Rooms are declarative bundles under `content/rooms/<slug>/`: a `room.yaml`
manifest, a target Dockerfile, lesson markdown, and a solver script. Start
from an existing bundle, then:

```sh
uv run cyberrange lint     # schema and writing-standard checks
make test-solvers          # prove the intended path solves cleanly
```

CI refuses content PRs that fail either gate. Curriculum authoring follows
the same pattern in `content/modules/` and `content/paths/`; see
`docs/content/catalog-status.md` for what exists and what gaps remain.

## Roadmap ideas

Tracked seriously now, not as a bullet list here. See
`docs/roadmap/implementation-status.md` for per-phase status and
`docs/content/catalog-status.md` for content targets vs reality.
