# Implementation status

Statuses: `not-started`, `in-progress`, `blocked`, `verified`. A
`verified` entry links to code, tests, and current evidence. "Scaffolded"
and "mostly done" are not statuses here. Plan of record:
`.hermes/plans/2026-08-22_224809-open-cyber-range-platform.md`.

## Phase 0 — Product contract, licensing, baseline preservation

| Item                                                                                            | Status      | Evidence                                                                                             |
| ----------------------------------------------------------------------------------------------- | ----------- | ---------------------------------------------------------------------------------------------------- |
| LICENSE AGPL-3.0-or-later                                                                       | verified    | `LICENSE`                                                                                            |
| Content licensing policy (CC BY-SA 4.0)                                                         | verified    | `docs/content-licensing.md`, `licenses/CC-BY-SA-4.0.txt`                                             |
| NOTICE, CONTRIBUTING, CODE_OF_CONDUCT, SECURITY                                                 | verified    | repo root                                                                                            |
| ADRs for stack, parity, isolation, packaging, flags, workstation, deployment, licensing, naming | verified    | `docs/decisions/0001`–`0009`                                                                         |
| Legacy 20-room demo captured as legacy-v0 profile with solver proof                             | verified    | `docker-compose.yml` profiles, `docs/evidence/2026-08-22-legacy-solve.txt` (20/20, 2975 pts, exit 0) |
| Migration inventory for all 20 rooms                                                            | verified    | `docs/legacy/migration-inventory.md`                                                                 |
| Semver + conventional commits + changelog automation config                                     | verified    | `CONTRIBUTING.md`, `cliff.toml`                                                                      |
| CODEOWNERS / protected main expectations                                                        | in-progress | `CODEOWNERS`; branch protection needs repo admin action after CI exists                              |

## Phase 1 — Monorepo, quality system, developer experience

| Item                                                                      | Status   | Evidence                                                           |
| ------------------------------------------------------------------------- | -------- | ------------------------------------------------------------------ |
| pnpm/Turborepo + uv workspaces, pinned toolchains                         | verified | `package.json`, `pnpm-lock.yaml`, root `pyproject.toml`, `uv.lock` |
| .editorconfig, ruff (lint+format), strict mypy, prettier, pre-commit      | verified | CI `python-check`/`node-check` green on PRs #2–#4                  |
| .env.example + typed fail-closed config validator                         | verified | `packages/config` + tests                                          |
| Compose profiles core/dev/legacy-v0 (+runner)                             | verified | `infra/compose/*.yml`; clean-install job green                     |
| Make targets incl. bootstrap/check/test/up/down/reset-demo/backup/restore | verified | `Makefile`; backup-restore proof passes                            |
| CI amd64 builds + arm64 build validation                                  | verified | `.github/workflows/ci.yml` arm64 job green                         |

## Phase 2 — API foundation, database, authentication

| Item                                                                                         | Status   | Evidence                                                        |
| -------------------------------------------------------------------------------------------- | -------- | --------------------------------------------------------------- |
| FastAPI app factory, request IDs, RFC 9457 errors, health/readiness, Alembic                 | verified | `apps/api/src/openrange/api/`; `api-integration` job green      |
| Local accounts, session cookies, CSRF, password reset, TOTP, recovery codes, device sessions | verified | 16 auth integration tests (`apps/api/tests/test_auth_flows.py`) |
| WebAuthn ceremonies, optional OIDC                                                           | verified | ceremony endpoints + tests; OIDC disabled unless configured     |
| RBAC permission catalogue                                                                    | verified | `apps/api/src/openrange/api/rbac.py`; guards test permissions   |
| Rate limiting, lockout/backoff, username rules                                               | verified | Redis limiter tests; lockout test proves 429                    |
| Setup wizard first-admin token                                                               | verified | `test_setup_wizard_creates_first_admin`                         |

## Phase 5 — Content SDK and declarative content format

| Item                                                                     | Status   | Evidence                                                    |
| ------------------------------------------------------------------------ | -------- | ----------------------------------------------------------- |
| Bundle schema (room/module/path) with JSON Schemas generated from models | verified | `packages/content-sdk/schemas/` via `cyberrange schemas`    |
| cyberrange CLI new/lint/solve/schemas/show/pack                          | verified | CLI runs in CI content jobs                                 |
| Lint engine incl. writing standards and branding guard                   | verified | `packages/content-sdk/tests/test_sdk.py`                    |
| Solver protocol + shared validators incl. per-session flags              | verified | same tests; validators reused by API submissions            |
| Docker harness with healthcheck, solve, reset proof                      | verified | `make test-solvers` = 20/20 PASS                            |
| All 20 legacy rooms migrated as v1 bundles                               | verified | `content/rooms/*`; full solver gate green locally and in CI |

## Phase 6 — Lab orchestrator and isolation boundary

| Item                                                                  | Status      | Evidence                                                             |
| --------------------------------------------------------------------- | ----------- | -------------------------------------------------------------------- |
| Runner agent per contract (HMAC, replay window, hardening, reconcile) | verified    | `docs/contracts/runner-api.md`; 16 runner integration tests          |
| Lab lifecycle state machine with event trail                          | verified    | `apps/api/src/openrange/api/labs/service.py`; labs integration tests |
| Per-user concurrency quota, extend/reset/stop, expiry reaper          | verified    | `apps/api/tests/test_labs.py`                                        |
| Cross-tenant isolation at API layer                                   | verified    | Bob gets 404 on Alice's lab in tests                                 |
| Egress default-deny (internal networks)                               | verified    | runner creates internal networks; lifecycle tests assert it          |
| Chaos: kill worker mid-transition → reconciliation                    | not-started | planned with worker phase                                            |

## Phases 3, 4, 7–15

Not started; sequenced next: gateway/terminal (Phase 7), web shell
(Phase 3), catalog (Phase 4), learning engine (Phase 8), scoring
(Phase 9), then Studio/orgs/community/ops/security/packaging.

## Human decisions pending (plan section 15)

These block public release only, not local implementation:

1. Final product name and identity (working title: OpenRange).
2. License confirmation (AGPL-3.0 + CC BY-SA 4.0 recommended).
3. Public domain, email/OAuth providers, telemetry/moderation policy.
4. Hardware/budget for clustered runners and licensed Windows images.
5. Whether community content/events ship enabled on first hosted instance.
6. External security review before claiming internet-ready cluster mode.
