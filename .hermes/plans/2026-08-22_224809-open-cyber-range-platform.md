# Open Cyber Range Platform Implementation Plan

**Goal:** Transform `home-ctf-box` from a 20-room LAN demo into a polished, safe, fully open-source cyber-learning platform with 100 original lab-backed rooms, structured courses, personal lab instances, browser workstations, competition, authoring tools, and production-grade self-hosting.

**Architecture:** Build a modular control plane (web, API, workers, data, search, object storage) separated from an untrusted lab data plane (per-user containers/VMs, isolated networks, runtime quotas, TTLs, and audited lifecycle operations). Ship a single-node Community Edition for one machine or a Raspberry Pi-class controller, plus a clustered deployment profile for serious multi-user installations; use the same APIs, content format, and UI in both modes.

**Tech Stack:** Next.js + TypeScript + Tailwind/shadcn for the web app; FastAPI + SQLAlchemy + Alembic for the API; PostgreSQL, Redis, Celery, S3-compatible storage, Meilisearch; Docker/Podman for single-node labs; Kubernetes plus gVisor/Kata/Firecracker-capable runners for clustered labs; xterm.js/SSH and Apache Guacamole/noVNC for browser workstations; OpenTelemetry, Prometheus, Grafana, Loki; Playwright, Vitest, pytest, k6, Trivy, Semgrep, and OWASP ZAP.

---

## 1. Owner, audience, target environments

- **Owner:** Adam and future project maintainers.
- **Contributors:** Changes stay in this repository. Do not deploy publicly, buy services, rotate credentials, or expose intentionally vulnerable targets without the maintainer's explicit approval.
- **Community Edition:** One Linux host, Docker or rootless Podman, 8 CPU/16 GB RAM recommended; reduced concurrency profile for Raspberry Pi 5. The Pi may run the control plane and light container rooms, but Windows/AD, nested virtualization, and multi-host ranges require a stronger x86_64 runner.
- **Cluster Edition:** Kubernetes on x86_64 nodes, ingress, PostgreSQL, Redis, object storage, isolated runner node pools, and optional VM-capable runtime.
- **Supported clients:** Current desktop/mobile browsers; desktop Chrome/Firefox/Safari/Edge are first-class for lab work. Mobile is first-class for reading, progress, and administration, but not claimed as a full terminal replacement.

## 2. Current baseline and constraints

The repository currently contains:

- A single 416-line Flask/SQLite platform in `platform/app.py` with inline HTML/CSS, username/password sessions, flag submission, and a global scoreboard.
- Twenty always-on Flask challenge containers registered manually in `docker-compose.yml`, each exposed on a fixed host port.
- Twenty deterministic web vulnerabilities and a strong end-to-end exploit proof in `scripts/demo-solve.sh` that confirms 20/20 solves and 2,975 points.
- A safe default bind to `127.0.0.1`, a Raspberry Pi deployment note, and multi-arch-friendly Python images.
- No committed history yet and all current files untracked; no tests beyond the demo solver, migrations, CI, license, API contract, observability, lab scheduler, per-user isolation, content schema, admin UI, course system, accessibility checks, or production security model.

Constraints and non-negotiables:

1. Preserve the 20 current exploits as regression fixtures and migrate them into the new content format; do not silently discard working content.
2. Never expose vulnerable services directly to the public internet. Public installations expose only the hardened control plane and a controlled lab gateway/VPN.
3. Every learner receives an isolated lab instance or isolated shared event instance. Flags are derived per user/team/session, not stored globally in Compose.
4. All training material must be original or compatibly licensed with attribution. Reproduce feature categories, not HTB/THM names, branding, prose, flags, assets, or challenge solutions.
5. The project remains usable without paid SaaS. Optional integrations must degrade gracefully.
6. Do not count generated placeholders as content. A room counts only when it passes instructional, technical, safety, accessibility, and solver-review gates.

## 3. Product benchmark and target scope

Official product documentation establishes the benchmark categories: HTB uses paths/modules/sections, interactive targets, browser workstations, notes, cheat sheets, machines, investigations, multi-host professional labs, seasons, and badges; TryHackMe uses walkthrough/challenge/network rooms, tasks and questions, browser AttackBoxes, learning paths, streaks, leagues, workspaces, and a content studio. Sources:

- [HTB Academy modules and paths](https://help.hackthebox.com/en/articles/12741910-academy-modules-paths)
- [HTB Labs content types](https://help.hackthebox.com/en/articles/5185158-introduction-to-htb-labs)
- [HTB Pro Labs](https://help.hackthebox.com/en/articles/5185470-how-to-play-pro-labs)
- [TryHackMe rooms](https://help.tryhackme.com/en/articles/6611837-rooms)
- [TryHackMe AttackBox](https://help.tryhackme.com/en/articles/6721845-the-attackbox-explained)
- [TryHackMe training portfolio](https://help.tryhackme.com/en/articles/8484133-training-content-overview)
- [TryHackMe room creation](https://help.tryhackme.com/en/articles/6495805-room-creation-overview)

Target feature families for the open-source platform:

- **Learn:** paths, modules, sections, theory, embedded questions, interactive tasks, prerequisites, estimates, objectives, cheat sheets, notes, bookmarks, glossary, progress, transcripts, and completion certificates.
- **Practice:** guided rooms, challenge rooms, Linux/Windows boxes, APIs, cloud simulations, reversing/pwn/crypto artifacts, blue-team investigations, and multi-host enterprise ranges.
- **Lab:** personal target instances, browser terminal/desktop, VPN access, start/extend/reset/stop, clear scope, credentials, countdown, snapshots where supported, and session recovery.
- **Compete:** all-time/monthly/seasonal boards, first blood, leagues, teams, events, tournaments, dynamic scoring, writeup embargoes, and anti-cheat review signals.
- **Community:** profiles, achievements, activity, room ratings, feedback, discussion links, teams, follows, public writeups after retirement, and contribution recognition.
- **Create and operate:** content SDK, local preview, declarative manifests, automated solvers, Content Studio, review workflow, publishing, scheduling, retirement, versioning, admin/support, analytics, and backups.

## 4. Definition of done

The project is complete only when all of these are true:

1. Fresh single-node install succeeds from documented commands and the setup wizard creates the first admin without editing source files.
2. The control plane has polished, responsive, accessible web UI for anonymous visitor, learner, author, reviewer, instructor, and administrator flows.
3. One hundred original lab-backed rooms are published across five difficulties and at least ten security domains; every room has an automated intended-path solver and reset/idempotency test.
4. At least 20 learning paths and 60 substantive modules contain a combined minimum of 300 lesson sections, 1,000 scored questions/tasks, 100 cheat sheets, and 20 capstones. Existing 20 micro-challenges may be reused inside those totals only after full migration and quality review.
5. Personal labs support start, readiness, access, extend, reset, stop, expiry, and cleanup. Two simultaneous learners cannot see, affect, or submit each other's flags or traffic.
6. Browser terminal works end-to-end; browser desktop works for GUI-designated content. VPN/manual connection is documented and tested.
7. Search/filtering, profiles, notes, bookmarks, progress, recommendations, streaks, achievements, teams, events, leaderboards, transcripts, and certificates pass acceptance tests.
8. Authors can create, preview, lint, solve-test, submit, review, publish, version, retire, and roll back content without modifying control-plane source.
9. CI verifies lint, types, unit, integration, contract, migrations, content schemas, every solver, Compose install, browser journeys, accessibility, security scans, and generated documentation.
10. A documented threat model is enforced: hardened control plane; untrusted data plane; default-deny egress; no Docker socket in web/API containers; scoped runner identity; secret encryption; rate limits; audit logs; backups and restore proof.
11. A 50-user clustered soak and a 5-user single-node soak meet published SLOs, with no orphan labs after forced worker/node failures.
12. Repository includes an OSI-approved license, contribution guide, code of conduct, security policy, content licensing policy, architecture docs, admin/operator guides, learner docs, author docs, and release notes.
13. No TODOs, mocked critical paths, fake telemetry, placeholder lessons, skipped required tests, or undocumented manual steps remain in release scope.

## 5. Target repository layout

```text
apps/
  web/                    # Next.js learner/admin/author UI
  api/                    # FastAPI control-plane API
  worker/                 # asynchronous jobs and scheduled work
  lab-gateway/            # authenticated TCP/HTTP/WebSocket routing
packages/
  ui/                     # design system and Storybook
  contracts/              # OpenAPI-generated TS client and shared schemas
  content-sdk/            # manifest schemas, CLI, lints, packager
  scoring/                # deterministic scoring/rank policy
  config/                 # shared validated configuration
infra/
  compose/                # single-node profiles and overrides
  kubernetes/             # Helm chart and policies
  terraform/              # optional reference deployment modules
  observability/          # dashboards, alerts, collectors
content/
  rooms/<slug>/           # manifest, tasks, assets, target, solver, tests
  modules/<slug>/         # lesson sections and assessments
  paths/<slug>/           # ordered modules/capstones
  shared/                 # glossary, citations, reusable assets
docs/
  architecture/ decisions/ operations/ authors/ learners/ security/
tests/
  e2e/ integration/ load/ security/ fixtures/
legacy/
  platform/ rooms/        # temporary during migration; removed at cutover
```

## 6. Core domain model

Create versioned migrations and typed APIs for:

- Identity: `users`, `identities`, `sessions`, `email_verifications`, `password_resets`, `mfa_factors`, `roles`, `permissions`, `user_roles`, `api_tokens`.
- Organizations: `organizations`, `memberships`, `groups`, `teams`, `team_members`, `invitations`, `assignments`, `cohorts`.
- Content: `content_items`, `content_versions`, `rooms`, `tasks`, `questions`, `answers`, `hints`, `solutions`, `files`, `targets`, `tags`, `skills`, `prerequisites`, `localizations`, `reviews`, `publication_events`.
- Curriculum: `paths`, `modules`, `sections`, join/order tables, enrollments, section progress, assessment attempts, mastery records.
- Runtime: `lab_templates`, `lab_instances`, `lab_targets`, `lab_networks`, `lab_routes`, `leases`, `runtime_events`, `cleanup_jobs`, `resource_usage`.
- Progress: `solves`, `task_completions`, `room_completions`, `notes`, `bookmarks`, `ratings`, `feedback`, `activity_events`, `skill_evidence`.
- Competition: `score_events` as an immutable ledger, `leaderboard_snapshots`, `seasons`, `events`, `event_members`, `first_bloods`, `leagues`, `league_memberships`, `achievements`, `achievement_grants`, `streaks`.
- Operations: `audit_events`, `notifications`, `notification_preferences`, `reports`, `moderation_cases`, `feature_flags`, `system_settings`, `outbox_events`.

Rules:

- UUID/ULID primary keys, UTC timestamps, soft retirement for published content, immutable content/version and score ledgers, idempotency keys for lifecycle and submissions.
- Per-session flags are HMAC-derived from a master key, user/team, room, task, and lab instance. Store only hashes where validation permits.
- Progress is attached to stable content identity plus version; content upgrades explicitly map or invalidate old progress.
- Every state mutation emits an audit/outbox event in the same transaction.

## 7. Execution roadmap

Each phase ends in a reviewable, green, releasable slice. Implementation uses test-first loops: add failing test, run and observe failure, implement, run focused test, run affected suite, commit. Exact commands become authoritative once bootstrap files exist.

### Phase 0 — Product contract, licensing, and baseline preservation

1. Add `LICENSE` (AGPL-3.0-or-later is the recommended default for a network platform), `NOTICE`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, and a content licensing policy (CC BY-SA 4.0 for prose/assets where contributors agree).
2. Record ADRs for web/API stack, single-node/cluster parity, data-plane isolation, content packaging, flag derivation, browser workstation, and deployment boundaries.
3. Capture the current 20-room demo as a `legacy-v0` Compose profile and record expected solver output.
4. Add a migration inventory mapping every current room, port, exploit, points value, and flag mechanism to its future slug/task.
5. Establish semantic versioning, conventional commits, changelog automation, ownership/CODEOWNERS, and protected main-branch expectations.

**Gate:** Legacy `docker compose up -d --build` and `scripts/demo-solve.sh` still pass before architecture changes; the exact output is archived as CI evidence.

### Phase 1 — Monorepo, quality system, and developer experience

1. Bootstrap `pnpm`/Turborepo for web/shared packages and `uv` for Python services; pin all runtime/tool versions.
2. Add `.editorconfig`, formatting, linting, strict TypeScript, mypy/pyright, Ruff, import rules, commit hooks, and generated-code boundaries.
3. Add `.env.example` with safe defaults and a typed configuration validator that fails closed.
4. Build Compose profiles: `core`, `dev`, `observability`, `workstation`, and `legacy-v0`.
5. Add Make/Task targets: `bootstrap`, `dev`, `check`, `test`, `test-e2e`, `content-check`, `up`, `down`, `reset-demo`, `backup`, `restore`.
6. Add CI for amd64 and arm64 image builds, dependency caching, SBOMs, image signing metadata, and artifact retention.
7. Add devcontainer and Codespaces-compatible setup without making either mandatory.

**Gate:** A clean clone reaches a healthy development stack with one documented command; `make check` is green on Linux amd64 and arm64 build validation.

### Phase 2 — API foundation, database, and authentication

1. Create FastAPI app factory, structured errors, request IDs, OpenAPI, health/readiness endpoints, database/session layers, and Alembic.
2. Implement local accounts, verified email option, secure session cookies, CSRF, password reset, TOTP/WebAuthn MFA, recovery codes, and device/session management.
3. Add OIDC login for self-hosters and optional GitHub/Google providers through configuration.
4. Implement RBAC for learner, author, reviewer, instructor, support, operator, and admin; permissions, not role names, protect endpoints.
5. Add rate limiting, lockout/backoff, compromised-password hook option, username rules, account export, and deletion workflow.
6. Seed admin only through one-time setup token/setup wizard; never ship default credentials.

**Gate:** Auth/RBAC integration tests cover fixation, CSRF, reset-token reuse, brute-force throttling, revoked sessions, privilege escalation, and tenant separation.

### Phase 3 — Design system and complete application shell

1. Define product name/identity distinct from HTB/THM; add tokens for color, type, spacing, motion, elevation, code, charts, dark/high-contrast modes.
2. Build accessible components in Storybook: navigation, command palette, cards, filters, progress, tables, forms, editor, Markdown, code block, task panel, terminal frame, timer, toasts, dialogs, charts, skeleton/error/empty states.
3. Build responsive shells for public marketing/docs, learner workspace, lab split view, Content Studio, organization dashboard, and admin console.
4. Add WCAG 2.2 AA semantics, keyboard flow, skip links, focus management, reduced motion, screen-reader live announcements, and color-independent status.
5. Add route-level loading/errors, offline-aware lesson drafts/notes, and installable PWA metadata for reading/progress.

**Gate:** Storybook visual regression, axe checks, keyboard-only journeys, mobile layouts at 320 px, and Lighthouse budgets pass.

### Phase 4 — Catalog, discovery, and profiles

1. Build home/dashboard with continue-learning, recommended next action, active lab, streak, skill progress, assignments, releases, and team activity.
2. Build unified library for rooms, boxes, investigations, modules, and paths with full-text search, facets, sort, favorites, recently viewed, and shareable query URLs.
3. Facets include difficulty, domain, skill, OS, runtime, target type, content type, guided/unguided, status, estimated time, language, creator, release date, and accessibility needs.
4. Build content detail pages with objectives, prerequisites, scope, target/workstation requirements, reviews, related learning, completion stats, and version/changelog.
5. Build public/private profiles with avatar, bio, skill radar, badges, rank, streak, completed content, certificates, activity, teams, and privacy controls.

**Gate:** Search index rebuild is idempotent; permission-filtered content never leaks through search; catalog and profile Playwright journeys pass.

### Phase 5 — Content SDK and declarative content format

1. Define JSON Schema/Pydantic models for `room.yaml`, `module.yaml`, `path.yaml`, targets, tasks, questions, hints, solutions, files, and licensing metadata.
2. A room bundle must include metadata, learning objectives, prerequisites, scope, difficulty evidence, estimated time, target topology, task graph, answer validators, tiered hints, full solution, author notes, reset hooks, healthcheck, solver, tests, citations, license, and safety declaration.
3. Implement `cyberrange content new|lint|build|preview|solve|test|pack|publish` CLI.
4. Add Markdown/MDX safety: sanitized output, fenced executable examples never auto-run, asset hashing, external-link checking, accessible image requirements, and citation validation.
5. Create validator types: exact, normalized, regex-with-timeout, numeric range, ordered/unordered set, per-session flag, file hash, and manual-review answer.
6. Generate catalog/API fixtures and docs from manifests. No challenge registration in application source.
7. Migrate the current 20 services and demo solver into 20 versioned room bundles while retaining behavioral equivalence.

**Gate:** One command validates and solves all 20 migrated rooms from clean builds; a deliberately malformed/unsafe bundle is rejected with actionable errors.

### Phase 6 — Lab orchestrator and isolation boundary

1. Implement lifecycle state machine: requested → scheduled → pulling → starting → health-checking → ready → extending/resetting → stopping → expired → cleaned/failed.
2. Build provider interface and Docker/Podman provider first; add Kubernetes provider second and VM provider only after isolation spikes pass.
3. Generate per-instance network, credentials, flags, DNS names, routes, and labels. Never reuse a learner's writable layer for another learner.
4. Enforce CPU/memory/PID/disk/time quotas, read-only roots where possible, dropped capabilities, seccomp/AppArmor/SELinux, non-root users, no-new-privileges, and host mount denylist.
5. Enforce default-deny lab egress; explicit room allowlists permit required targets/package mirrors. Block cloud metadata, RFC1918 control-plane networks, host gateway, Docker/Kubernetes APIs, and DNS rebinding routes.
6. Put runner operations behind a narrow authenticated agent; web/API never mounts the Docker socket or holds cluster-admin credentials.
7. Add reconciliation and garbage collection for orphan containers, networks, routes, volumes, reservations, and expired secrets.
8. Add capacity accounting, fair queue, concurrency quota, backpressure, warm pools for popular immutable images, and admin drain/maintenance modes.
9. Support shared team/event instances separately from personal instances; every mode shows its collaboration implications before start.

**Gate:** Automated cross-tenant tests fail to access another lab/control plane/host; chaos tests kill workers/runners mid-transition and reconciliation leaves no orphaned resources.

### Phase 7 — Lab gateway, VPN, terminal, and desktop

1. Route labs by opaque instance route through an authenticated gateway; do not allocate public host ports per room.
2. Provide WireGuard configuration per user/device with revocation, scoped routes, QR/download flow, connection diagnostics, and clear scope rules.
3. Add xterm.js browser terminal connected through a short-lived SSH/WebSocket token, terminal resizing, clipboard guardrails, reconnect, font/theme controls, and downloadable transcript under user control.
4. Add Guacamole/noVNC browser desktop for GUI rooms, fullscreen, dynamic resolution, reconnect, and credential display/copy controls.
5. Add persistent attacker workstation as opt-in; default ephemeral workstation starts from a versioned tool image. Scan images and publish tool manifests.
6. Lab panel exposes address, credentials, time remaining, extend/reset/stop, status timeline, scope, clipboard actions, and troubleshooting bundle.
7. Ensure closing a browser does not accidentally stop a lab; expiry reminders and explicit termination do.

**Gate:** Start and use target from browser and VPN, reset it, survive browser reconnect, expire it, and prove route/secret revocation in Playwright/integration tests.

### Phase 8 — Learning engine

1. Implement path → module → section hierarchy with ordered and optional branches, prerequisites, enrollment, pause/resume, estimated time, and versioned progress.
2. Section blocks: prose, callout, code, quiz, answer, file, video/embed allowlist, target, terminal, checkpoint, reflection, and capstone.
3. Build split learning view with table of contents, reading pane, lab/workstation, questions, notes, bookmarks, glossary, cheat sheet, and contextual hint drawer.
4. Add autosaved per-content notes with Markdown, search, export, and privacy. Add global and per-module cheat sheets.
5. Support progressive hints with optional point/XP cost, delayed/full solutions, and author-configurable retirement/writeup embargo.
6. Track attempts, time-on-task as a non-scoring signal, completion, mastery, skill evidence, and recommended remediation—never infer mastery from page views alone.
7. Generate downloadable transcript and verifiable completion certificate for paths; call these certificates of completion, not industry certifications.
8. Add localization framework with protected code/command spans and contributor review; ship English first and prove one sample translated module end-to-end.

**Gate:** A new user completes onboarding → path → theory → browser lab → questions → capstone → transcript/certificate without admin intervention.

### Phase 9 — Scoring, progression, and competition

1. Use immutable score events and deterministic projections for XP, rank, room points, event score, hints, first blood, and reversals.
2. Separate learning XP from competitive score so guided content cannot overwhelm challenge rankings.
3. Add all-time, monthly, seasonal, room, path, team, organization, and event leaderboards with privacy and opt-out controls.
4. Add configurable seasons, scheduled releases, tiered divisions, promotions/demotions, first blood, decay rules, frozen final snapshots, and replayable calculation.
5. Add daily/weekly streaks based on meaningful completion, timezone-safe windows, one configurable freeze, and healthy reminders without dark patterns.
6. Add achievements/badges for breadth, depth, consistency, events, contributions, blue/red specialties, and accessibility-positive behaviors; all rules are data-driven.
7. Add teams, invitations, roles, team feed, shared event sessions, team boards, and fair attribution.
8. Add event/tournament builder: registration window, content pool, release schedule, dynamic/static scoring, team size, visibility, scoreboard freeze, announcements, and export.
9. Add anti-cheat signals: impossible timing, answer spraying, flag reuse, session mismatch, request provenance, collusion patterns, and manual review. Do not silently ban or use opaque ML as the sole decision.

**Gate:** Property tests prove score replay determinism and no double awards; season rollover, timezone boundaries, ties, reversals, and scoreboard freeze pass simulation.

### Phase 10 — Content Studio and publishing workflow

1. Build browser Studio for room/module/path creation with autosave, preview, task ordering, question/hint/solution editing, topology editor, assets, citations, license, and accessibility checklist.
2. Allow Git-native editing to remain first-class; Studio imports/exports the same bundle format and creates reviewable revisions.
3. Workflow: draft → validation failed/ready → submitted → technical review → instructional review → security review → approved → scheduled → published → updated/retired.
4. Require two-person approval for public content; prevent author self-approval unless explicitly enabled for a private single-admin installation.
5. Add reviewer diffs, inline comments, checklist, solver logs, preview deployment, conflict handling, and audit history.
6. Add release scheduling, announcement, version pinning, rollback, retirement, writeup unlock, and broken-content emergency disable.
7. Build contributor dashboard with status, reviewer feedback, published content, quality metrics, and attribution.

**Gate:** An author creates a room in Studio, previews and solve-tests it, a reviewer rejects then approves it, it publishes on schedule, and an operator rolls it back without source edits.

### Phase 11 — Organizations, cohorts, and instructor tooling

1. Add organizations/workspaces with groups, cohorts, role assignments, invitations, SSO configuration, and tenant-scoped branding.
2. Instructors create assignments from paths/modules/rooms, deadlines, prerequisites, optional hints/solutions, attempts, and accommodations.
3. Dashboards show completion, mastery evidence, common failure points, lab usage, and at-risk learners without exposing sensitive terminal/network content by default.
4. Add CSV/JSON exports, learner transcript export, and minimal LTI/SCORM/xAPI integration after core flows stabilize.
5. Add private content libraries and custom paths without forking upstream content.

**Gate:** Cross-organization authorization suite passes; instructor can assign, learner complete, and instructor export results with correct privacy.

### Phase 12 — Community, support, and notifications

1. Add room ratings and structured feedback (accuracy, difficulty, stability, instructional quality) only after meaningful interaction.
2. Add spoiler-aware comments/discussion links and public writeup links gated by author policy/retirement.
3. Add in-app notification center and optional email/webhook delivery for lab expiry, assignments, reviews, releases, teams, events, and security notices.
4. Add report-content/report-user flows, moderation queue, evidence retention policy, actions, appeals notes, and audit trail.
5. Add support bundle generation containing redacted configuration, service versions, lab event timeline, and correlation IDs—never flags, passwords, tokens, notes, or terminal history by default.

**Gate:** Notification preference/opt-out tests pass; moderation/support roles cannot access unrelated secrets or private learner data.

### Phase 13 — Observability, reliability, and operations

1. Instrument API, workers, gateway, and runners with OpenTelemetry traces, metrics, and structured redacted logs.
2. Dashboards: API health/latency/errors, queue depth, lab lifecycle/failures/start latency, capacity, orphan cleanup, gateway traffic, database, cache, content solver health, and learner journey failures.
3. Alerts include symptom, impact, runbook, and safe first action. Avoid alerting on expected vulnerable target behavior.
4. Implement encrypted backups for PostgreSQL/object storage/config secrets, retention, restore to clean environment, and documented RPO/RTO.
5. Add database migration preflight, backward-compatible rollout rules, maintenance mode, runner drain, and rollback playbooks.
6. Add audit export, data retention controls, privacy export/deletion, and redaction verification.

**SLO targets:** 99.9% control-plane availability in cluster mode; p95 API read <300 ms; p95 container lab ready <30 s warm/<90 s cold; zero known orphan labs after 15-minute reconciliation; restore proof each release.

**Gate:** Restore latest backup into an empty stack and pass smoke tests; forced worker/database/runner disruptions produce actionable alerts and recover within published bounds.

### Phase 14 — Security engineering

1. Threat-model identities, control plane, author supply chain, content renderers, runner API, lab gateway, workstation, VPN, artifact downloads, plugins/integrations, and admin operations.
2. Add SAST, dependency/container/IaC scanning, secrets scanning, SBOM, provenance, signature verification, license policy, and malicious content-bundle fixtures.
3. Add API authorization matrix tests, tenant isolation tests, SSRF tests, archive traversal/decompression bomb tests, Markdown XSS tests, WebSocket origin/auth tests, and runner escape defense tests.
4. Encrypt secrets at rest with envelope keys; support rotation; never log flags/tokens/passwords; redact URLs/query strings where secrets may appear.
5. Establish vulnerability disclosure process, supported versions, patch SLA, security advisories, and release signing.
6. Commission an external review before claiming internet-ready cluster mode. Until then label releases self-hosted beta and keep vulnerable data plane private.

**Gate:** No unresolved critical/high control-plane findings; every accepted risk has owner, rationale, compensating control, and review date. Data-plane escape testing is documented and repeatable.

### Phase 15 — Packaging and deployment

1. Publish signed multi-arch images and immutable tags; never rely on floating `latest` in production docs.
2. Single-node installer checks OS, architecture, virtualization, disk/RAM/ports, generates secrets, starts core services, creates admin setup token, and runs smoke tests.
3. Provide Pi profile with arm64 images, reduced workers/concurrency, no VM labs, and external-runner registration for heavy content.
4. Provide Helm chart with Pod Security, NetworkPolicy, resource requests/limits, autoscaling, runner node taints, ingress/TLS, external database/object-store options, and upgrade hooks.
5. Publish offline bundle procedure for classrooms: images, content, signatures, checksums, licenses, and import command.
6. Document reverse proxy, TLS, DNS, email, OIDC, object storage, backup, monitoring, scaling, updates, rollback, and disaster recovery.

**Gate:** Clean installs and upgrades from previous release pass on amd64 and arm64 single-node; cluster install passes in ephemeral Kubernetes; rollback preserves data.

## 8. Launch content program: 100 original lab-backed rooms

All rooms require an original scenario, objectives, prerequisites, scope, 3-tier hints, full solution, automated solver, healthcheck, reset test, per-session answer/flag, estimated time, difficulty rubric, accessibility review, citations, and license. Names below are working titles and must pass trademark/search review.

### Track A — Web and API foundations (rooms 001–025)

1. Busted Login — beginner — SQL authentication bypass (migrate current).
2. Nosy Files — beginner — path traversal (migrate current).
3. Ping of Doom — easy — command injection (migrate current).
4. SSTI Greeting — easy — template injection (migrate current).
5. Token Forger — medium — JWT algorithm confusion (migrate current).
6. IDOR Invoices — beginner — object authorization (migrate current).
7. Open Panels — beginner — exposed diagnostics (migrate current).
8. Cookie Shapeshifter — beginner — client-side trust (migrate current).
9. Regex Doom — easy — regex injection (migrate current).
10. Mass Assign — easy — mass assignment (migrate current).
11. XXE Importer — medium — XML entities (migrate current).
12. Pickle Jar — medium — unsafe deserialization (migrate current).
13. Trusted Proxy — beginner — proxy header trust (migrate current).
14. Wrong Method — beginner — verb authorization (migrate current).
15. Open Closet — beginner — exposed backups (migrate current).
16. Predictable Reset — easy — weak reset tokens (migrate current).
17. Double Trouble — easy — parameter pollution (migrate current).
18. Fetch Boy — easy — SSRF with isolated internal target (migrate current).
19. Union Vault — easy — UNION SQL injection (migrate current).
20. Brace Yourself — easy — format-string injection (migrate current).
21. Cartographer — easy — API discovery and hidden routes.
22. Tenant Trouble — medium — multi-tenant authorization chain.
23. Graph Maze — medium — GraphQL introspection, batching, and auth.
24. Cache Me Outside — hard — cache poisoning and normalization.
25. Race to Zero — hard — transactional race condition with deterministic harness.

### Track B — Linux, networking, and privilege escalation (rooms 026–045)

26. First Shell — beginner — ports, banners, SSH, and flags.
27. Paper Permissions — beginner — Unix ownership and readable secrets.
28. Scheduled Surprise — easy — writable cron script escalation.
29. Sudo Side Door — easy — constrained sudo misconfiguration.
30. SUID Story — easy — unsafe SUID binary.
31. Capable Enough — easy — Linux capabilities abuse.
32. Path of Least Resistance — easy — PATH hijacking.
33. Service Please — medium — systemd unit/environment escalation.
34. Container Window — medium — container enumeration and safe breakout simulation.
35. NFS No Boundaries — medium — NFS permissions/root squash.
36. Knock Knock — beginner — TCP/UDP enumeration and port knocking.
37. DNS Breadcrumbs — easy — DNS records, transfer, and virtual hosts.
38. Proxy Pivot — medium — SOCKS pivot through two isolated hosts.
39. Route Less Traveled — medium — subnet routing and service discovery.
40. Packet Diary — easy — PCAP analysis and credential hygiene.
41. Mailroom — medium — SMTP enumeration and mail trust chain.
42. Shared Secrets — medium — SMB/NFS credential reuse.
43. Kernel of Truth — hard — version analysis and safe simulated kernel exploit.
44. Namespace Escape Plan — hard — namespace/cgroup misconfiguration.
45. Quiet Persistence — hard — Linux compromise investigation and cleanup report.

### Track C — Windows and Active Directory (rooms 046–065)

46. Windows Welcome — beginner — PowerShell, services, users, and flags.
47. Service Accounted — easy — service permissions escalation.
48. Registry Keys — easy — registry-stored credentials.
49. Quoted Intentions — easy — unquoted service path.
50. Token Gesture — medium — Windows token impersonation concept lab.
51. Share and Share Alike — beginner — SMB shares and ACLs.
52. Name Resolution — easy — LLMNR/NBT-NS poisoning in an isolated network.
53. Spray Day — easy — password policy and controlled spraying.
54. Graph the Domain — easy — AD enumeration and relationship mapping.
55. Ticket Booth — medium — Kerberoasting.
56. AS-REP Arcade — medium — pre-authentication weakness.
57. Delegated Trust — medium — delegation abuse.
58. Certificate Misprint — hard — AD CS misconfiguration.
59. Relay Station — hard — NTLM relay in a closed network.
60. GPO Gone Wrong — hard — Group Policy permissions.
61. Forest Footpath — hard — child/parent trust path.
62. Backup Operator — medium — backup privilege abuse.
63. Blue Screenplay — medium — Windows event log investigation.
64. Directory Recovery — hard — ransomware-style AD incident recovery.
65. Crown Jewels — insane — five-host AD capstone with report deliverable.

### Track D — Crypto, reversing, binary, mobile, and hardware concepts (rooms 066–080)

66. Encoding Is Not Encryption — beginner — encodings and hashes.
67. Reused Horizon — easy — XOR keystream reuse.
68. Padding Post — medium — CBC padding oracle.
69. Tiny RSA — medium — weak RSA parameters.
70. Signed Twice — hard — nonce reuse in signatures.
71. Strings Attached — beginner — static binary triage.
72. Branch Manager — easy — control flow and patching.
73. License to Learn — easy — debugger basics.
74. Stack Snacks — medium — basic stack overflow with mitigations taught.
75. Return Address — hard — ROP chain in a purpose-built binary.
76. Heap House — insane — deterministic heap exploitation capstone.
77. APK Breadcrumbs — easy — Android static analysis.
78. Intentional Leak — medium — Android intents/storage/API chain.
79. Firmware Pantry — medium — firmware extraction and credential discovery.
80. Signal in the Noise — hard — simple RF/IoT artifact investigation without live transmission.

### Track E — Defensive, cloud, DevSecOps, and enterprise ranges (rooms 081–100)

81. Alert One — beginner — SOC alert triage.
82. Phish Food — beginner — headers, URLs, and attachment metadata.
83. Web Trail — easy — web access-log investigation.
84. Memory Lane — medium — memory artifact analysis.
85. Disk Detective — medium — filesystem timeline investigation.
86. CloudTrail of Crumbs — easy — AWS-style audit-log analysis using local simulation.
87. Bucket Brigade — easy — object-storage policy exposure in local cloud emulator.
88. Role Play — medium — cloud IAM privilege escalation in local emulator.
89. Function Junction — medium — serverless secret and event abuse simulation.
90. Kubernetes Paper Walls — medium — RBAC/service-account escalation in nested lab cluster.
91. Pipeline Spill — easy — CI log/artifact secret leakage.
92. Dependency Confusion Lab — medium — isolated package registry supply-chain chain.
93. Image Issues — medium — container image analysis and runtime hardening.
94. Detection Forge — hard — write and validate Sigma/YARA detections against fixtures.
95. Threat Hunt Northstar — hard — multi-source threat hunt with hypothesis/report.
96. MiniCorp Breach — hard — three-host red-team range.
97. MiniCorp Defense — hard — matching blue-team investigation of room 096.
98. Purple Replay — hard — execute safe emulation and tune detections.
99. Cloud Company — insane — multi-service local-cloud attack/defense capstone.
100. Full Spectrum — insane — multi-host red/blue capstone requiring evidence and professional report.

Difficulty distribution at launch: 20 beginner, 30 easy, 30 medium, 15 hard, 5 insane. At least 30 rooms are guided walkthroughs, at least 50 are unguided challenges/boxes, at least 10 are defensive investigations, and at least 5 are multi-host ranges. Some rooms satisfy multiple categories.

## 9. Curriculum: 20 paths and at least 60 modules

Each path ends in one or more of the rooms above as practical capstones. Each module contains 4–8 substantive sections, assessments, one cheat sheet, and at least one interactive exercise.

1. **Start Here: Cyber Foundations** — ethics/scope, networking, Linux, Windows, web, terminal, evidence, first room.
2. **Linux Operator** — shell, files, users, processes, services, packages, logs, networking, scripting.
3. **Windows Operator** — PowerShell, registry, services, event logs, identity, remote administration.
4. **Networking for Security** — TCP/IP, routing, DNS, HTTP, TLS, VPNs, Wireshark, pivoting.
5. **Web Pentester I** — HTTP, discovery, auth, access control, injection, browser tooling, reporting.
6. **Web Pentester II** — deserialization, SSRF, request smuggling/cache, races, GraphQL, multi-tenant testing.
7. **API Security** — REST/GraphQL, OAuth/OIDC, tokens, BOLA, rate limits, mass assignment, testing methodology.
8. **Linux Privilege Escalation** — enumeration, permissions, sudo/SUID, services, cron, capabilities, containers.
9. **Windows Privilege Escalation** — enumeration, services, tokens, registry, scheduled tasks, credential material.
10. **Active Directory Attack** — identity graph, Kerberos, delegation, AD CS, relay, trusts, operational safety.
11. **SOC Analyst I** — triage, logs, SIEM concepts, network/web/email alerts, case notes.
12. **SOC Analyst II** — endpoint telemetry, threat hunting, memory/disk, detection tuning, incident timeline.
13. **DFIR Investigator** — evidence handling, filesystems, memory, timelines, reporting, malware-safe workflow.
14. **Malware and Reversing Foundations** — assembly, static/dynamic analysis, debugging, unpacking concepts, YARA.
15. **Binary Exploitation** — C memory, stack, mitigations, ROP, heap foundations.
16. **Applied Cryptography Attacks** — encoding/hashes, symmetric modes, oracles, RSA, signatures, protocol mistakes.
17. **Cloud Security** — shared responsibility, IAM, storage, audit logs, serverless, attack paths, remediation.
18. **Kubernetes and Container Security** — images, namespaces, RBAC, secrets, network policy, runtime detection.
19. **DevSecOps and Supply Chain** — CI/CD, secret handling, dependencies, SBOM/provenance, scanning, response.
20. **Professional Security Engagement** — scoping, rules of engagement, evidence, risk, remediation, executive/technical reporting, full-spectrum capstone.

Content production procedure:

1. Write a curriculum map linking every objective → lesson → assessment → room/task → skill evidence.
2. Create three-room vertical slice first: beginner walkthrough, medium personal box, blue-team artifact case.
3. Calibrate with at least three independent playtesters per difficulty band; record median time, hint usage, failure modes, unintended solves, and rating.
4. Produce in batches of ten rooms and six modules. A batch cannot merge until every item passes the quality gate.
5. Run automated solvers nightly and after base-image/dependency updates. Quarantine broken content automatically from new starts while preserving operator override and evidence.
6. Review all lessons at least every six months; security/tool claims include sources and review date.

## 10. API and event contract

Minimum stable API groups:

- `/auth`, `/users`, `/profiles`, `/organizations`, `/teams`, `/invites`.
- `/catalog`, `/content`, `/paths`, `/modules`, `/sections`, `/tasks`, `/questions`, `/search`.
- `/enrollments`, `/progress`, `/attempts`, `/notes`, `/bookmarks`, `/ratings`, `/certificates`.
- `/labs`, `/workstations`, `/vpn`, `/routes`, `/capacity`.
- `/scores`, `/leaderboards`, `/seasons`, `/leagues`, `/events`, `/achievements`, `/streaks`.
- `/studio`, `/reviews`, `/publications`, `/moderation`, `/admin`, `/audit`, `/system`.

Use cursor pagination, explicit filtering/sorting, ETags for content, idempotency keys for creates/submissions/lifecycle actions, optimistic concurrency for authoring, RFC 9457-style problems, generated OpenAPI client, and version compatibility tests. Webhooks use signed timestamped payloads, replay protection, retry/backoff, delivery logs, and secret rotation.

## 11. Testing and validation matrix

Required commands by release candidate (wire these exact targets even if underlying tools evolve):

```bash
make bootstrap
make check
make test-unit
make test-integration
make test-contract
make test-content
make test-solvers
make test-e2e
make test-a11y
make test-security
make test-load
make test-compose-clean-install
make test-backup-restore
```

Suites:

- Unit/property: policies, scoring, flags, validators, manifests, state machines, quotas, permissions, recommendation rules.
- Integration: PostgreSQL/Redis/S3/search/outbox, migrations up/down where safe, runner lifecycle, gateway routes, VPN issuance/revocation.
- Content: schema, links/assets/licenses/citations, build, health, reset, intended solver, unintended shortcut checks, resource limits.
- Browser: all critical learner/author/reviewer/admin journeys, reconnect/error/retry, mobile read flows, multi-role access denial.
- Security: control-plane ZAP baseline, XSS/CSRF/SSRF/archive bombs/WebSocket auth, tenant/lab isolation, secret redaction, malicious bundle.
- Accessibility: axe, keyboard-only, screen reader spot checks, contrast, zoom/reflow, reduced motion.
- Load: 50-user cluster and 5-user single node; start storms, submissions, leaderboard snapshots, search, WebSockets, expiry cleanup.
- Chaos: API/worker/runner restart, lost events, database failover simulation, expired tokens, partial image pulls, disk pressure, network partition.

Release acceptance journey:

1. Install clean stack.
2. Create admin, author, reviewer, instructor, two learners, two teams, and two organizations.
3. Publish one new room and module through review.
4. Enroll learners, start isolated labs concurrently, connect by browser and VPN, solve, request hint, reset, and complete.
5. Verify progress, XP, score, achievement, streak, team/event boards, notes, transcript, and certificate.
6. Prove neither learner nor organization can access the other's lab, progress, notes, flags, admin data, or search results.
7. Expire/stop labs, kill a runner during cleanup, and prove reconciliation.
8. Back up, destroy the test deployment, restore, and repeat smoke test.

## 12. Security allowlist and denylist

**Agent/operator may do without further approval:** local repository edits; local builds/tests; disposable local containers/networks/volumes specifically labeled for this project; generated test users/secrets; local benchmark and security scans; documentation and original content creation.

**Requires Adam's approval:** public deployment or DNS/TLS changes; binding vulnerable targets beyond loopback/private controlled networks; cloud accounts/resources or purchases; production database migrations; real email/OAuth providers; sending messages/invites; collecting real user telemetry; publishing images/packages/releases; installing privileged kernel/runtime components; external penetration tests.

**Always forbidden:** copying proprietary competitor content; committing credentials/real flags/private keys; mounting host root or broad home directories into labs; giving lab containers Docker socket/cluster-admin; permitting unrestricted egress by default; malware execution outside a purpose-built isolated environment; destructive workspace resets; testing systems outside explicit scope.

## 13. Rollout and rollback

1. Release `0.1` as migrated legacy content plus new control-plane/auth/catalog shell.
2. Release `0.2` with personal container labs, gateway, browser terminal, and first three gold-standard rooms.
3. Release `0.3` with learning engine, first five paths/15 modules/40 rooms, Studio alpha, and organizations.
4. Release `0.4` with 75 rooms, defensive artifacts, workstation desktop, events/seasons, Kubernetes beta, and security review.
5. Release `1.0` only at the full definition of done: 100 rooms, 20 paths/60 modules, single-node and cluster proof, external security review disposition, restore/load evidence, complete docs.

For every release:

- Database changes use expand/migrate/contract sequencing and a tested backup.
- Content publishes immutable versions; rollback selects the prior version and prevents new starts on the bad version while existing sessions finish or receive explicit reset notice.
- Images use immutable digest; rollback updates desired digest and reconciles.
- Feature flags can disable Studio publishing, events, workstation, or specific lab providers without disabling core learning.
- Legacy stack remains available only until migrated-room solver parity and one release of burn-in; then archive it, do not maintain two production platforms indefinitely.

## 14. Principal risks and mitigations

- **Host compromise from intentional vulnerabilities:** treat targets as hostile; rootless/sandboxed runtime, deny egress, dedicated runner nodes, no host mounts/socket, patched host, external review.
- **Content volume crushes quality:** content SDK, automated solver/reset tests, batch gates, independent technical/instructional reviews, playtest metrics, quarantine broken content.
- **Pi cannot run HTB-scale workloads:** make Pi a supported light controller/runner profile, state hard limits, support remote x86/VM runners, never fake Windows/nested virtualization support.
- **Architecture becomes too broad to finish:** vertical slices and release gates; one provider first; defer optional integrations until critical learner/author/operator loops are proven.
- **Cheating dominates rankings:** per-session flags, event isolation, immutable ledger, provenance signals, manual review/appeal, learning XP separated from competition.
- **Generated lessons are inaccurate or unsafe:** require sources, technical reviewer, solver, playtesting, content review date, and clear lab scope.
- **Open-source maintainership overload:** contribution templates, reviewer queues, ownership, content health automation, stable schemas, plugin boundaries, release/support policy.
- **Legal/brand confusion:** unique name/design, original content, compatible licenses/attribution, trademark review before public release.
- **Privacy overcollection:** data minimization, explicit telemetry setting, short retention, export/deletion, no terminal capture by default, audited support access.

## 15. Human decisions required before public 1.0, but not before local implementation

Adam must eventually choose or approve:

1. Final project/product name and visual identity.
2. Code/content licenses (recommended AGPL-3.0-or-later + CC BY-SA 4.0) after considering contributor and hosting goals.
3. Public domain, email provider, OAuth providers, telemetry policy, moderation policy, and privacy/legal text.
4. Hardware/budget for clustered runner and Windows/AD content; licenses for Windows evaluation images must be handled lawfully and cannot be redistributed in the repository.
5. Whether public community content, organizations, and competitive events are enabled on the first hosted instance.
6. Acceptance of external security review findings and any time-bounded risks before internet exposure.

Use safe local defaults and feature flags so these decisions do not block development.

## 16. First implementation sequence

Start here, in this order:

1. Preserve and prove the 20-room baseline.
2. Add licensing/ADRs and bootstrap the monorepo/CI.
3. Build one complete vertical slice: account → catalog → lesson → personal lab → browser terminal → flag/task → progress → score → cleanup.
4. Build the content schema/CLI and migrate three representative current rooms, then all twenty.
5. Harden/reconcile the container runner and prove tenant isolation before adding more content or public access.
6. Finish the learner UI and learning hierarchy with one production-quality path.
7. Build Studio/review/publishing against the same content format.
8. Scale content in reviewed batches while parallel platform phases proceed.
9. Add competitions, organizations, workstation desktop, cluster provider, and advanced lab types only after the core slice is stable.
10. Run full security/load/restore/release gates; do not call the platform complete until every item in Section 4 has current evidence.

## 17. Completion reporting contract

Maintain `docs/roadmap/implementation-status.md` with every phase/task marked `not-started`, `in-progress`, `blocked`, or `verified`. Every `verified` entry links to code, tests, and current command output/artifact. Maintain `docs/content/catalog-status.md` with all 100 rooms and all path/module/section totals, review state, solver state, playtest state, and last health date. At each release, report:

- What changed and why.
- Exact files/migrations/content versions.
- Exact validation run and results.
- Definition-of-done items newly proven.
- Remaining incomplete items and blockers.
- Security findings disposition.
- Deployment/rollback notes.

“Scaffolded,” “mostly complete,” “tests skipped,” and “left as an exercise” never count as done.
