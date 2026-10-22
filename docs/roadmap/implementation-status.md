# Implementation status

Item statuses follow the plan section 17 contract: `not-started`,
`in-progress`, or `verified`. Every `verified` row cites code, tests,
or a CI run you can re-check. Phase summaries use four labels:
`done`, `core-done` (phase core merged; remaining items listed),
`partial` (some items merged, others not started), and `todo`.

Plan of record:
`.hermes/plans/2026-08-22_224809-open-cyber-range-platform.md`.
Last updated 2026-10-22. The previous snapshot was main commit `ddbc21e`
(PR #54) on 2026-08-24.

CI note that colors every run citation below: the last green CI run on
main is 32709414616 (success, 2026-08-24 09:02 UTC). Every later ci and
content run on main fails with zero steps executed in every job, which
points at the Actions runner never starting rather than at any test
failure. Local proof numbers from this machine are cited alongside.

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
| 7     | Lab gateway and terminal             | done      |
| 8     | Learning engine                      | core-done |
| 9     | Scoring and competition              | core-done |
| 10    | Content Studio                       | core-done |
| 11    | Organizations and instructor tooling | core-done |
| 12    | Community, support, notifications    | core-done |
| 13    | Observability and operations         | core-done |
| 14    | Security engineering                 | partial   |
| 15    | Packaging and deployment             | core-done |

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

| Item                                                                                                                                                                               | Status   | Evidence                                                                                   |
| ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- | ------------------------------------------------------------------------------------------ |
| pnpm + Turborepo + uv workspaces                                                                                                                                                   | verified | `package.json`, `pnpm-workspace.yaml`, `turbo.json`, root `pyproject.toml`, `uv.lock`      |
| ruff lint/format, strict mypy, prettier, pre-commit                                                                                                                                | verified | `make check` recipe (`Makefile:21`); CI `ci.yml` node job runs `pnpm exec turbo run check` |
| Compose profiles core/dev/runner/gateway/observability/production/legacy-v0                                                                                                        | verified | `infra/compose/*.yml`; root compose includes core+dev                                      |
| Make targets bootstrap/check/test/test-integration/test-content/test-solvers/up/down/reset-demo/backup/restore/clean-install/backup-restore/build-images/push-images/release-check | verified | `Makefile`; `tests/install/compose-clean-install.sh`, `tests/install/backup-restore.sh`    |
| Local unit suite green on this machine, 2026-08-24                                                                                                                                 | verified | `uv run pytest -m "not integration and not e2e and not slow"`: 49 passed                   |

Remaining: `make test-contract`, `test-security`, and `test-load` still
print a message and exit 1 (`Makefile:35`, `Makefile:53`, `Makefile:56`).
`make test-e2e` and `make test-a11y` run the Playwright suite
(`Makefile:47`, `Makefile:50`). Each leftover placeholder is tracked under
its owning phase below. Main CI has failed since 10:00 UTC on 2026-08-24
for environmental reasons (see the note at the top); local runs are the
current proof of record.

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

| Item                                             | Status   | Evidence                                                                                                                                                                                                                                          |
| ------------------------------------------------ | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Design-system package with tokens and components | verified | `packages/ui/src/tokens.css`, `packages/ui/src/components/`, stories under `packages/ui/src/stories/`                                                                                                                                             |
| Learner web app routes                           | verified | `apps/web/app/catalog`, `dashboard`, `labs`, `login`, `register`, `profile` (PR #5); learning view, challenge board, terminal page, and notifications inbox added by PR #54 under `apps/web/app/learn`, `challenges`, `terminal`, `notifications` |
| Playwright e2e specs                             | verified | `apps/web/tests/e2e/` (17 passed locally on 2026-10-22); `make test-e2e` and `make test-a11y`; CI job `web-e2e` in `.github/workflows/ci.yml`                                                                                                     |

Remaining:

1. Author/admin UI surfaces for studio and orgs (APIs exist; web routes do not).

## Phase 5: content SDK and declarative content format

Status: done.

| Item                                                             | Status   | Evidence                                                                                                                                               |
| ---------------------------------------------------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Bundle schema (room/module/path) with generated JSON Schemas     | verified | `packages/content-sdk/src/openrange/content/models.py`, schema check via `cyberrange schemas --check-diff` in `.github/workflows/content.yml`          |
| cyberrange CLI (lint, solve_all, schemas)                        | verified | `packages/content-sdk/src/openrange/content/cli.py`, `solve_all.py`                                                                                    |
| Lint engine incl. path/module ref resolution and capstone checks | verified | `packages/content-sdk/src/openrange/content/linting/`; PR #11 fixed module-ref resolution                                                              |
| Solver protocol, Docker harness, reset/idempotency proof         | verified | `packages/content-sdk/src/openrange/content/solver/`, `packages/content-sdk/src/openrange/content/harness/`; elevated SSH target profile in PR #8      |
| external_image wrapper support with digest-pinned upstream refs  | verified | schema field at `models.py:123`, harness pull path at `harness/__init__.py:249` and `:307`, lint rules for static-answer rooms, four shipped bundles   |
| Localization framework with protected spans                      | verified | `packages/content-sdk/src/openrange/content/i18n.py`, `docs/i18n.md`, Hungarian sample validated by `packages/content-sdk/tests/test_i18n.py` (PR #52) |
| All 109 room bundles pass lint on this machine, 2026-08-24       | verified | programmatic `lint_room` pass over `content/rooms/*`: 109 bundles, 0 errors, 0 warnings                                                                |

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

## Phase 7: lab gateway, terminal, desktop

Status: done.

| Item                                                 | Status   | Evidence                                                                                                                                                       |
| ---------------------------------------------------- | -------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Authenticated gateway with HTTP proxy to lab targets | verified | `apps/lab-gateway/`; `apps/lab-gateway/tests/test_proxy.py` (12 test functions)                                                                                |
| Browser SSH terminal                                 | verified | `apps/lab-gateway/tests/test_terminal.py` (13 test functions)                                                                                                  |
| Browser desktop bridge for GUI content               | verified | WebSocket-to-RFB bridge in `apps/lab-gateway/src/openrange/gateway/desktop.py`; `test_desktop.py` (15 tests)                                                   |
| Gateway tokens and health endpoints                  | verified | `test_tokens.py` (11), `test_health.py` (4)                                                                                                                    |
| Gateway compose service                              | verified | `infra/compose/gateway.yml`                                                                                                                                    |
| VPN device lifecycle documented and wired            | verified | `apps/api/src/openrange/api/vpn/routes.py` (5 endpoints incl. config QR and status), `docs/contracts/vpn-api.md`, gateway heartbeat client inside `desktop.py` |

Remaining: a WireGuard peer watcher that feeds the heartbeat endpoint;
the client ships, the watcher does not exist yet.

## Phase 8: learning engine

Status: core-done.

| Item                                                               | Status   | Evidence                                                                                                                                                           |
| ------------------------------------------------------------------ | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Enrollment, progress, section completion, notes/bookmarks surfaces | verified | `apps/api/src/openrange/api/learning/` (15 route handlers); `apps/api/tests/test_learning.py`, `test_learning_content.py`                                          |
| Catalog query API backing the web catalog                          | verified | same package; consumed by `apps/web/app/catalog`                                                                                                                   |
| Learning view in the web app                                       | verified | `apps/web/app/learn/page.tsx` plus per-path route under `apps/web/app/learn/[pathSlug]` (PR #54)                                                                   |
| Streaks with timezone safety, freezes, healthy milestones          | verified | `apps/api/src/openrange/api/streaks/engine.py` (pure function of injected date, timezone, freeze days), `routes.py` (3 endpoints); `test_streaks.py` (17) (PR #53) |
| Locale-aware content delivery                                      | verified | i18n validation and locale negotiation per `docs/i18n.md`; `apps/api/tests/test_learning_i18n.py` (PR #52)                                                         |

Remaining: recommendations. Achievements ship through scoring
(`GET /api/scoring/me/achievements`) and reach the notification feed.

## Phase 9: scoring, progression, competition

Status: core-done.

| Item                                                                                   | Status   | Evidence                                                                                                                                                                             |
| -------------------------------------------------------------------------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Scoring engine: flag submission, first-blood, projection                               | verified | `apps/api/src/openrange/api/scoring/` (8 route handlers, `projection.py`); tests `test_scoring_api.py` (10) and `test_scoring_projection.py` (7)                                     |
| Leaderboards incl. monthly periods                                                     | verified | `GET /leaderboards/{scope}` in `apps/api/src/openrange/api/scoring/routes.py`                                                                                                        |
| Jeopardy challenges: containerless tasks, attachments, files portal, submissions audit | verified | `apps/api/src/openrange/api/challenges/routes.py` (7 endpoints incl. `GET /{slug}/files/{file_id}`), category enum incl. osint at `routes.py:32`; `test_challenges.py` (15) (PR #43) |
| Dynamic scoring in two places                                                          | verified | linear decay in `apps/api/src/openrange/api/challenges/service.py` (`validate_decay`, floors after `solves_to_floor`); CTFd-style decay in `events/service.py:70`                    |
| Teams with invites and member roles                                                    | verified | `apps/api/src/openrange/api/teams/routes.py` (7 endpoints); `test_teams.py` (7) (PR #39)                                                                                             |
| Events builder with frozen scoreboards                                                 | verified | `apps/api/src/openrange/api/events/routes.py` (7 endpoints incl. scoreboard refresh); `test_events.py` (8) (PR #39)                                                                  |

Remaining: learner transcripts, team-vs-team red/blue objective split,
king-of-the-hill mode (see the gap list below).

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

| Item                                                                        | Status   | Evidence                                                                                                                                                  |
| --------------------------------------------------------------------------- | -------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Announcements, per-user preferences, notification feed, email outbox worker | verified | `apps/api/src/openrange/api/notifications/` (routes 9 handlers, `email.py`, `worker.py`); `apps/api/tests/test_notifications.py` (7)                      |
| Notifications inbox in the web app                                          | verified | `apps/web/app/notifications/page.tsx` plus `apps/web/components/NotificationsView.tsx` covering achievement, assignment, and announcement events (PR #54) |
| Community events                                                            | verified | events builder listed under phase 9 (PR #39)                                                                                                              |
| Dev mail sink                                                               | verified | Mailpit service in `infra/compose/dev.yml`                                                                                                                |

Remaining: support flows beyond notifications and events.

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

Status: core-done.

| Item                                              | Status      | Evidence                                                                                           |
| ------------------------------------------------- | ----------- | -------------------------------------------------------------------------------------------------- |
| Production images for api, web, gateway           | verified    | `docker/Dockerfile.api`, `docker/Dockerfile.web`, `docker/Dockerfile.gateway`; `make build-images` |
| Production compose stack with ops profile         | verified    | `infra/compose/production.yml`; compose validation runs inside `make release-check`                |
| Tag-triggered release pipeline publishing to GHCR | verified    | `.github/workflows/release.yml` (`on: push: tags: ['v*']`, build then push matrix)                 |
| Install and upgrade documentation                 | verified    | `docs/deployment.md` (fresh install, upgrade, rollback, TLS, sizing)                               |
| First tagged release published                    | in-progress | pipeline exists but no `v*` tag has been pushed (`git tag` is empty)                               |

Remaining: cut the first tagged release so the pipeline proves itself end
to end; cluster-mode deployment story stays blocked behind phase 14
hardening and the external review.

## Launch content program (plan sections 8 and 9)

Live numbers live in `docs/content/catalog-status.md`. Headline as of
2026-08-24 at `ddbc21e`: 109 room bundles authored and gate-green
(tracks A through F complete plus four external-image wrappers),
18 of 20 paths, 54 modules, 324 sections, 181 scored questions,
54 cheat sheets, 13 capstone references across 10 paths.

## Remaining known gaps

Carried from `docs/platforms/integration-matrix.md` minus everything
closed by the last two days of merges:

1. Attack-defense king-of-the-hill mode (echoCTF.RED, FBCTF). No shared
   cohort-facing target or capture timer exists anywhere in apps or content.
2. Achievement toast and badge shelf. Achievements land in the notification
   feed, but nothing fires an earn-time toast and the profile page has no
   badge shelf.
3. Randomized per-instance vulnerable apps (SecGen). The runner builds
   exactly what each bundle ships; there is no randomization manifest.
4. Network-capture replay labs (CyberDefenders). No room replays a capture
   as live traffic.
5. Crackme-style reverse boards (Crackmes.one). Narrowed: jeopardy
   attachments plus `file_hash` validators exist; binaries embedding a
   per-session flag do not.
6. Learner-facing code-review challenges (Code Review Lab). No code-review
   validator type exists in the bundle schema.
7. Team-vs-team red/blue scoring split (echoCTF.RED, FBCTF, VulnArena).
   Narrowed: teams, events, and frozen scoreboards ship; role-based
   red/blue objectives do not.

Closed since the matrix was written: hint economy (costed hint tiers in
room bundles, spends recorded as hint events and surfaced as
`hint_cost_total` in transcripts), challenge file downloads
(`GET /api/challenges/{slug}/files/{file_id}`), dynamic score decay (two
implementations cited under phase 9), OSINT category (accepted enum value
in the jeopardy challenge schema at `challenges/routes.py:32`), and the
wrapper-bundle mechanism itself (external_image support, phase 5).

Also open, outside the matrix: branch protection on main (repo-admin
action), e2e and accessibility gates, chaos drill, load soaks, first
tagged release, recommendations, transcripts, studio version history,
and authoring UIs for studio and org admins.

## Human decisions pending (plan section 15)

Unchanged and still blocking public release only:

1. Final product name and identity (working title: OpenRange).
2. License confirmation AGPL-3.0 + CC BY-SA 4.0.
3. Public domain, email/OAuth providers, telemetry/moderation policy.
4. Hardware/budget for clustered runners and licensed Windows images.
5. Whether community content/events ship enabled on first hosted instance.
6. External security review.

## Changelog

### 2026-08-24, second wave (evening)

Twenty-one PRs merged between `b4a9e8c` and head `ddbc21e`, covering
#34 through #54:

- #54 web: learning view, jeopardy board UI, terminal embed, notifications
  inbox.
- #53 streaks with timezone safety, freezes, healthy milestones.
- #52 localization framework with protected spans and Hungarian sample.
- #51 rooms 076-080, track D finale.
- #50 rooms 051-055, active directory concepts batch 2.
- #49 CI fix: retry pip-audit on transient PyPI advisory API failures.
- #48 rooms 101-105, classic vulnerable machine boxes, new track F.
- #47 platform integration matrix covering 54 CTF/lab platforms
  (`docs/platforms/integration-matrix.md`).
- #46 rooms 096-100, enterprise capstone finale.
- #45 rooms 091-095, devsecops and supply chain.
- #44 external OSS lab wrappers: Juice Shop, DVWA, WebGoat, WrongSecrets,
  digest-pinned official images (`docs/labs-external.md`).
- #43 jeopardy challenges with attachments, files portal, dynamic scoring,
  submissions audit.
- #42 rooms 086-090, cloud and k8s concepts track E batch 2.
- #41 rooms 081-085, soc and dfir foundations track E batch 1.
- #40 lint fix: drop unused noqa on loopback placeholder.
- #39 teams, events builder, frozen scoreboards (phase 9 remainder).
- #38 rooms 071-075, reversing and binary foundations track D batch 2.
- #37 rooms 061-065, track C finale including crown jewels capstone.
- #36 rooms 056-060, advanced AD concepts batch 3.
- #35 curriculum wave 6: DFIR, kubernetes container security, and
  professional engagement paths.
- #34 rooms 066-070, crypto attacks track D batch 1.

One unnumbered commit also landed: `c4b8214`, gateway test skip when the
host already occupies port 5900.

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
