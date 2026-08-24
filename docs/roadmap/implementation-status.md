# Implementation status

Item statuses follow the plan section 17 contract: `not-started`,
`in-progress`, or `verified`. Every `verified` row cites code, tests,
or a CI run you can re-check. Phase summaries use four labels:
`done`, `core-done` (phase core merged; remaining items listed),
`partial` (some items merged, others not started), and `todo`.

Plan of record:
`.hermes/plans/2026-08-22_224809-open-cyber-range-platform.md`.
Last updated 2026-08-24 at main commit `b4a9e8c` (PR #27).

## Phase summary

| Phase | Scope                                | Status    |
| ----- | ------------------------------------ | --------- |
| 0     | Governance, licensing, baseline      | core-done |
| 1     | Monorepo, quality system, DX         | core-done |
| 2     | API foundation, auth, database       | done      |
| 3     | Design system and app shell          | core-done |
| 4     | Catalog and discovery                | core-done |
| 5     | Content SDK and content format       | done      |
| 6     | Lab orchestrator and isolation       | core-done |
| 7     | Lab gateway and terminal             | core-done |
| 8     | Learning engine                      | core-done |
| 9     | Scoring and competition              | core-done |
| 10    | Content Studio                       | core-done |
| 11    | Organizations and instructor tooling | core-done |
| 12    | Community, support, notifications    | core-done |
| 13    | Observability and operations         | core-done |
| 14    | Security engineering                 | partial   |
| 15    | Packaging and deployment             | todo      |

## Phase 0: governance, licensing, baseline preservation

| Item                                                                 | Status      | Evidence                                                                                                                   |
| -------------------------------------------------------------------- | ----------- | -------------------------------------------------------------------------------------------------------------------------- |
| LICENSE AGPL-3.0-or-later                                            | verified    | `LICENSE`                                                                                                                  |
| Content licensing policy CC BY-SA 4.0                                | verified    | `docs/content-licensing.md`, `licenses/CC-BY-SA-4.0.txt`                                                                   |
| NOTICE, CONTRIBUTING, CODE_OF_CONDUCT, SECURITY                      | verified    | repo root                                                                                                                  |
| ADRs 0001 to 0009                                                    | verified    | `docs/decisions/`                                                                                                          |
| Legacy 20-room demo preserved as legacy-v0 profile with solver proof | verified    | root `docker-compose.yml` profile `legacy-v0`; `docs/evidence/2026-08-22-legacy-solve.txt` (20/20 rooms, 2975 pts, exit 0) |
| Migration inventory for all 20 rooms                                 | verified    | `docs/legacy/migration-inventory.md`                                                                                       |
| Semver + conventional commits + changelog config                     | verified    | `CONTRIBUTING.md`, `cliff.toml`                                                                                            |
| CODEOWNERS / branch protection on main                               | in-progress | `CODEOWNERS` exists; protection still needs a repo-admin action                                                            |

Remaining: enable branch protection on main.

## Phase 1: monorepo, quality system, developer experience

| Item                                                                                                                                        | Status   | Evidence                                                                                   |
| ------------------------------------------------------------------------------------------------------------------------------------------- | -------- | ------------------------------------------------------------------------------------------ |
| pnpm + Turborepo + uv workspaces                                                                                                            | verified | `package.json`, `pnpm-workspace.yaml`, `turbo.json`, root `pyproject.toml`, `uv.lock`      |
| ruff lint/format, strict mypy, prettier, pre-commit                                                                                         | verified | `make check` recipe (`Makefile:20`); CI `ci.yml` node job runs `pnpm exec turbo run check` |
| Compose profiles core/dev/runner/gateway/observability/legacy-v0                                                                            | verified | `infra/compose/*.yml`; root compose includes core+dev                                      |
| Make targets bootstrap/check/test/test-integration/test-content/test-solvers/up/down/reset-demo/backup/restore/clean-install/backup-restore | verified | `Makefile`; `tests/install/compose-clean-install.sh`, `tests/install/backup-restore.sh`    |
| Latest main CI green                                                                                                                        | verified | run 32680234417, success, 2026-08-24 (`gh run list -b main`)                               |

Remaining: `make test-contract`, `test-e2e`, `test-a11y`, `test-security`, and
`test-load` are still placeholders that print and exit 1 (`Makefile:35`,
`Makefile:47`, `Makefile:50`, `Makefile:53`, `Makefile:56`). Each is tracked
under its owning phase below.

## Phase 2: API foundation, database, authentication

Status: done.

| Item                                                                         | Status   | Evidence                                                                                                                             |
| ---------------------------------------------------------------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| FastAPI app factory, request IDs, RFC 9457 errors, health/readiness, Alembic | verified | `apps/api/src/openrange/api/main.py`, `errors.py`, `health.py`, `readiness.py`, `apps/api/src/openrange/api/db/`                     |
| Local accounts, sessions, CSRF, password reset, TOTP, recovery codes         | verified | `apps/api/src/openrange/api/auth/routes.py`; tests in `apps/api/tests/test_auth_flows.py`                                            |
| WebAuthn ceremonies, optional OIDC                                           | verified | `apps/api/src/openrange/api/auth/webauthn_routes.py`, `apps/api/src/openrange/api/auth/oidc_routes.py`; OIDC inert unless configured |
| RBAC permission catalogue                                                    | verified | `apps/api/src/openrange/api/rbac.py`                                                                                                 |
| Rate limiting and lockout/backoff                                            | verified | `apps/api/src/openrange/api/middleware.py` (`RateLimitMiddleware`)                                                                   |
| Setup wizard first-admin token                                               | verified | `apps/api/src/openrange/api/setup/routes.py`; `apps/api/tests/test_security_setup_token.py`                                          |
| Security headers hardening                                                   | verified | `apps/api/tests/test_security_headers.py` (PR #27)                                                                                   |

Remaining: exercise OIDC against a real provider before any hosted launch.

## Phases 3 and 4: design system, learner web shell, catalog

Status: core-done.

| Item                                             | Status      | Evidence                                                                                              |
| ------------------------------------------------ | ----------- | ----------------------------------------------------------------------------------------------------- |
| Design-system package with tokens and components | verified    | `packages/ui/src/tokens.css`, `packages/ui/src/components/`, stories under `packages/ui/src/stories/` |
| Learner web app routes                           | verified    | `apps/web/app/catalog`, `dashboard`, `labs`, `login`, `register`, `profile` (PR #5)                   |
| Playwright e2e specs                             | in-progress | `apps/web/tests/e2e/a11y.spec.ts`, `keyboard-journey.spec.ts` exist; nothing runs them                |

Remaining:

1. Wire `make test-e2e` and `make test-a11y` to the existing Playwright specs
   and add both to CI. Both targets are currently exit-1 stubs.
2. Author/admin UI surfaces for studio and orgs (APIs exist; web routes do not).

## Phase 5: content SDK and declarative content format

Status: done.

| Item                                                             | Status   | Evidence                                                                                                                                          |
| ---------------------------------------------------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| Bundle schema (room/module/path) with generated JSON Schemas     | verified | `packages/content-sdk/src/openrange/content/models.py`, schema check via `cyberrange schemas --check-diff` in `.github/workflows/content.yml`     |
| cyberrange CLI (lint, solve_all, schemas)                        | verified | `packages/content-sdk/src/openrange/content/cli.py`, `solve_all.py`                                                                               |
| Lint engine incl. path/module ref resolution and capstone checks | verified | `packages/content-sdk/src/openrange/content/linting/`; PR #11 fixed module-ref resolution                                                         |
| Solver protocol, Docker harness, reset/idempotency proof         | verified | `packages/content-sdk/src/openrange/content/solver/`, `packages/content-sdk/src/openrange/content/harness/`; elevated SSH target profile in PR #8 |
| All 50 room bundles pass lint + solver shards in CI              | verified | `.github/workflows/content.yml` runs `cyberrange lint` plus 4 solver shards; latest green content run on main: 32680139689, success, 2026-08-24   |

Remaining: none blocking phase scope; per-room review state is tracked in
`docs/content/catalog-status.md`.

## Phase 6: lab orchestrator and isolation boundary

Status: core-done.

| Item                                                                  | Status   | Evidence                                                                                                                        |
| --------------------------------------------------------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------- |
| Runner agent with HMAC auth, replay window, reconcile loop            | verified | `apps/lab-runner/`; tests in `apps/lab-runner/tests/test_auth.py`, `test_lifecycle.py`, `test_reconcile.py` (15 test functions) |
| Lab lifecycle state machine, quotas, extend/reset/stop, expiry reaper | verified | `apps/api/src/openrange/api/labs/` (6 route handlers); `apps/api/tests/test_labs.py`                                            |
| Cross-tenant isolation at API layer                                   | verified | Bob gets 404 on Alice's lab in `apps/api/tests/test_labs.py`                                                                    |
| Egress default-deny internal networks                                 | verified | runner creates internal networks; asserted in lifecycle tests                                                                   |

Remaining: chaos drill that kills a worker mid-transition and proves
reconciliation. Planned since the first version of this file, still absent.

## Phase 7: lab gateway, terminal

Status: core-done.

| Item                                                 | Status   | Evidence                                                                        |
| ---------------------------------------------------- | -------- | ------------------------------------------------------------------------------- |
| Authenticated gateway with HTTP proxy to lab targets | verified | `apps/lab-gateway/`; `apps/lab-gateway/tests/test_proxy.py` (12 test functions) |
| Browser SSH terminal                                 | verified | `apps/lab-gateway/tests/test_terminal.py` (13 test functions)                   |
| Gateway tokens and health endpoints                  | verified | `test_tokens.py` (11), `test_health.py` (4)                                     |
| Gateway compose service                              | verified | `infra/compose/gateway.yml`                                                     |

Remaining: browser desktop for GUI-designated content; documented VPN/manual
connection path (plan section 4 item 6).

## Phase 8: learning engine

Status: core-done.

| Item                                                               | Status   | Evidence                                                                                                                  |
| ------------------------------------------------------------------ | -------- | ------------------------------------------------------------------------------------------------------------------------- |
| Enrollment, progress, section completion, notes/bookmarks surfaces | verified | `apps/api/src/openrange/api/learning/` (15 route handlers); `apps/api/tests/test_learning.py`, `test_learning_content.py` |
| Catalog query API backing the web catalog                          | verified | same package; consumed by `apps/web/app/catalog`                                                                          |

Remaining: recommendations, streaks, achievements. Grep for these in
`apps/api/src/openrange/api/learning/` returns nothing today.

## Phase 9: scoring, progression, competition

Status: core-done.

| Item                                                     | Status   | Evidence                                                                                                                                         |
| -------------------------------------------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| Scoring engine: flag submission, first-blood, projection | verified | `apps/api/src/openrange/api/scoring/` (8 route handlers, `projection.py`); tests `test_scoring_api.py` (10) and `test_scoring_projection.py` (7) |
| Leaderboards incl. monthly periods                       | verified | `GET /leaderboards/{scope}` in `apps/api/src/openrange/api/scoring/routes.py`                                                                    |

Remaining: teams, events, transcripts, certificates.

## Phase 10: Content Studio

Status: core-done.

| Item                                    | Status   | Evidence                                                                                                                        |
| --------------------------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------- |
| Drafts, review workflow, atomic publish | verified | `apps/api/src/openrange/api/studio/` (13 route handlers); `apps/api/tests/test_studio.py` (10), `test_studio_workspace.py` (10) |

Remaining: version history, retire, rollback endpoints; authoring UI.

## Phase 11: organizations, cohorts, instructor tooling

Status: core-done.

| Item                                         | Status   | Evidence                                                                                                              |
| -------------------------------------------- | -------- | --------------------------------------------------------------------------------------------------------------------- |
| Orgs, cohorts, invites, instructor endpoints | verified | `apps/api/src/openrange/api/orgs/` (18 route handlers); `apps/api/tests/test_orgs.py` (7), `test_orgs_invites.py` (4) |

Remaining: instructor dashboards in the web app.

## Phase 12: community, support, notifications

Status: core-done.

| Item                                                                        | Status   | Evidence                                                                                                                             |
| --------------------------------------------------------------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| Announcements, per-user preferences, notification feed, email outbox worker | verified | `apps/api/src/openrange/api/notifications/` (routes 9 handlers, `email.py`, `worker.py`); `apps/api/tests/test_notifications.py` (7) |
| Dev mail sink                                                               | verified | Mailpit service in `infra/compose/dev.yml`                                                                                           |

Remaining: community events and support flows beyond notifications.

## Phase 13: observability, reliability, operations

Status: core-done.

| Item                                                     | Status   | Evidence                                                                                                     |
| -------------------------------------------------------- | -------- | ------------------------------------------------------------------------------------------------------------ |
| Prometheus, Grafana, Loki, promtail, node-exporter stack | verified | `infra/compose/observability.yml`, `infra/observability/`                                                    |
| Readiness probes and metrics middleware + endpoint       | verified | `apps/api/src/openrange/api/readiness.py`, `metrics.py`; `apps/api/tests/test_metrics.py` (5)                |
| Backup and restore tooling with smoke test               | verified | `scripts/backup.sh`, `scripts/restore.sh`, `make backup` / `make restore`, `tests/install/backup-restore.sh` |

Remaining: k6 load soaks and published SLOs (`make test-load` is an exit-1
stub); the chaos drill from phase 6 doubles as the forced-failure soak input.

## Phase 14: security engineering

Status: partial.

| Item                                                                      | Status   | Evidence                                                                                                                                  |
| ------------------------------------------------------------------------- | -------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| Automated gates: bandit SAST, pip-audit, pnpm audit, gitleaks secret scan | verified | `.github/workflows/security.yml` (gitleaks v8.24.3 CLI, `bandit -r apps/api -ll`, `pip-audit -r requirements-audit.txt`); `gitleaks.toml` |
| Threat model document                                                     | verified | `security/threat-model.md`                                                                                                                |
| Hardening fixes on API responses                                          | verified | security headers tests added in PR #27                                                                                                    |

Remaining:

1. ZAP baseline scan named in the Makefile help text does not exist anywhere;
   either add it or fix the help text.
2. External security review before claiming internet-ready cluster mode
   (plan section 15 decision 6).
3. Cluster-mode hardening work (multi-runner threat model enforcement).

## Phase 15: packaging and deployment

Status: todo.

Nothing shipped yet beyond `cliff.toml`. No release workflow exists
(`ls .github/workflows` shows only `ci.yml`, `content.yml`, `security.yml`).
Remaining: release pipeline, image publishing, versioned release notes,
install docs for single-node and clustered deployment.

## Launch content program (plan sections 8 and 9)

Live numbers live in `docs/content/catalog-status.md`. Headline as of
2026-08-24: 50 of 100 rooms authored and gate-green (tracks A and B complete,
C 5 of 20, D and E empty), 12 of 20 paths, 36 modules, 216 sections,
115 scored questions, 36 cheat sheets, 11 capstone references.

## Human decisions pending (plan section 15)

Unchanged and still blocking public release only:

1. Final product name and identity (working title: OpenRange).
2. License confirmation AGPL-3.0 + CC BY-SA 4.0.
3. Public domain, email/OAuth providers, telemetry/moderation policy.
4. Hardware/budget for clustered runners and licensed Windows images.
5. Whether community content/events ship enabled on first hosted instance.
6. External security review.

## Changelog

### 2026-08-24

Fifteen merges landed on main today, head now `b4a9e8c`:

- #27 phase 14 core: security.yml gates (bandit, pip-audit, pnpm audit,
  gitleaks) plus API hardening fixes.
- #26 phase 10 core: studio drafts, review, atomic publish.
- #24 phase 13 core: observability stack, readiness probes, backup tooling.
- #23 phase 12: notifications core with email outbox.
- #17 phase 11 core: organizations, cohorts, instructor tooling.
- #14 phase 9 core: scoring engine and leaderboards.
- #28 rooms 046-050, first track C (windows-ad) batch.
- #29 curriculum wave 4 (SOC II, cloud, DevSecOps paths).
- #25 curriculum wave 3.
- #20 curriculum wave 2.
- #18 curriculum wave 1.
- #16 rooms 041-045 finishing track B.
- #13 rooms 036-040 track B networking.
- #12 rooms 031-035 track B privesc and services.
- #21 review fixes for rooms 026-030.

### 2026-08-23

Foundation wave: governance (#1), monorepo (#2), API foundation (#3),
content SDK and legacy migration (#4), web shell phases 3-4 (#5), rooms
021-025 (#6), SSH harness (#8), learning engine (#9), lab gateway (#10),
lint_path fix (#11), rooms 026-030 (#7), uv workspace fix (#22).
