# OpenRange threat model

Phase 14 core deliverable. Scope: the control plane (web + API), lab
gateway, runner agent, and content harness as shipped in this
repository. The data plane (learner lab containers) is untrusted by
design; everything here assumes a hostile data plane.

Status legend for mitigations: **shipped** (in code today),
**partial** (some coverage, gap noted), **planned** (tracked, not built).

## Trust boundaries

```
Internet ──> control plane (Next.js web + FastAPI API)  [trusted boundary]
                    │  HMAC-signed API, scoped token
                    ├──> runner agent (Docker/Podman host)  [semi-trusted]
                    │        └──> lab containers            [untrusted]
                    └──> lab gateway (TCP/WS routing)       [untrusted traffic in, scoped egress out]
Learner browser ──> web app; never touches the runner directly.
```

## Data classification

| Class              | Examples                                                                                         | Handling rules                                                           |
| ------------------ | ------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------ |
| Public             | room catalogs, published content, leaderboards of opted-in users                                 | cacheable                                                                |
| Learner private    | progress, notes, enrollments, email                                                              | session/bearer auth, tenant-scoped queries                               |
| Credentials        | passwords (argon2id hashes), session tokens (SHA-256 hashed at rest), TOTP seeds, recovery codes | never logged, hashed or encrypted at rest                                |
| Platform secrets   | `secret_key`, `flag_master_key`, `runner_api_token`, S3/Meili credentials                        | env/settings only, fail-closed outside dev, never committed              |
| Challenge material | per-session derived flags, room-bundle fixture flags                                             | per-user HMAC derivation; static bundle flags are training fixtures only |
| Audit/safety       | score ledger, anti-cheat signals, login attempts                                                 | append-only where possible, admin-visible                                |

## STRIDE analysis: top 12 threats

| #   | Threat                                                            | Stride             | Boundary        | Mitigation                                                                                                                                             | Status  |
| --- | ----------------------------------------------------------------- | ------------------ | --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ | ------- |
| 1   | Credential stuffing / brute force on `/api/auth/login`            | Spoofing           | Internet→API    | Redis sliding-window limits (20/5min) + DB lockout (10 tries/15min), argon2id hashing, uniform errors                                                  | shipped |
| 2   | Session theft via XSS or network interception                     | Spoofing/Tampering | Browser→API     | HttpOnly+Secure+Strict cookies, CSRF double-check on mutations (`x-csrf-token`), Secure=false only in dev env                                          | shipped |
| 3   | Privilege escalation to admin routes (`/admin/*`)                 | Elevation          | Learner→API     | Permission-based guards: scoring uses `require_permission("settings:write")`; notifications `_require(...)`; RBAC permissions not role names           | shipped |
| 4   | Cross-tenant access to another learner's lab or flags             | Info disclosure    | API→labs        | `_own_instance` ownership check on every lab route, 404 (not 403) to avoid existence leaks, `lab:manage-any` gated escape hatch                        | shipped |
| 5   | Unauthenticated runner abuse (container create/delete)            | Spoofing/Tampering | API→runner      | HMAC-SHA256 request signing with timestamp over body; runner token required outside dev (fail-closed settings)                                         | shipped |
| 6   | Lab container escapes to runner host or control-plane network     | Elevation          | Runner→host     | Per-instance networks, CPU/mem/PID quotas, TTL cleanup, planned gVisor/Kata profile and default-deny egress allowlists                                 | partial |
| 7   | Malicious content bundle (solver/harness code exec at build time) | Tampering          | Author→platform | Bundles are declarative manifests; API never imports solver code at runtime; harness runs isolated. Review workflow gates publishing                   | partial |
| 8   | Setup wizard re-run hijacks first-admin creation                  | Elevation          | Internet→API    | One-time random token held only in process memory, constant-time comparison, closes forever after first user exists                                    | shipped |
| 9   | Secrets leaked through git history or logs                        | Info disclosure    | Repo/CI         | Gitleaks gate with narrow allowlist for intentional challenge fixtures; secrets from env only; flags logged as fingerprints only                       | shipped |
| 10  | Vulnerable dependencies (Python/npm supply chain)                 | Tampering          | Build→runtime   | Weekly+PR security workflow: bandit `-ll`, pip-audit on exported lockfile, `pnpm audit --prod --audit-level=high`; overrides pin patched postcss/sharp | shipped |
| 11  | Clickjacking / MIME sniffing / referrer leakage of API responses  | Info disclosure    | Browser→API     | Baseline headers on every response: `X-Frame-Options: DENY`, `nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`, CSP `default-src 'none'`   | shipped |
| 12  | OIDC provider confusion / authorization-code interception         | Spoofing           | IdP→API         | PKCE S256, state cookie double-submit, discovery fetch with timeout, provider errors surface as 502 without stack traces                               | shipped |

## Accepted risks

Each entry needs an owner, rationale, compensating control, and review
date per the phase gate.

1. **Asserts used as internal invariants in request paths**
   (`apps/api/src/openrange/api/**`, bandit B101 low). Owner: platform
   maintainers. Rationale: they mark programmer-error states after
   database reads that cannot legitimately be null; converting them is
   churn without a threat reduction today. Compensating control:
   bandit gate runs at `-ll` so these stay visible; integration tests
   exercise the guarded routes. Review date: first external security
   review.
2. **Static challenge flags inside `content/rooms/**` bundles**.
   Owner: content maintainers. Rationale: room targets are training
   fixtures by design; their "secrets" are the product. Compensating
   controls: gitleaks allowlist limited to `content/rooms/*/target/**`
   and `room.yaml` plus legacy `rooms/`, `platform/`; production rooms
   move to per-session derived flags (`per_session_flag` validator).
   Review date: whenever a room migrates to per-session flags.
3. **Gateway/runner bind `0.0.0.0` inside compose**. Owner: infra
   maintainers. Rationale: container-internal binds; exposure is
   governed by compose network topology, not the bind address.
   Compensating control: runner API requires signed requests; gateway
   routes only opaque instance IDs. Review date: cluster-edition design.
4. **Rate limiter fails open when Redis is unreachable**. Owner:
   platform maintainers. Rationale: availability of login beats strict
   limiting for a self-hostable platform; DB lockout still applies.
   Compensating control: error log alerting hook documented; lockout
   path independent of Redis. Review date: phase 13 SLO work.

## Incident response contacts (placeholder)

To be filled before any public deployment:

- Security contact / disclosure inbox: `security@openrange.invalid`
  (replace with real monitored address)
- Primary incident owner: Adam (repository owner)
- Escalation path: maintainers group, then infrastructure owner
- Disclosure process: see `SECURITY.md`; advisories published with
  releases once supported-version policy lands.

## Dependency policy

- Python deps resolve from `uv.lock`; audits run against an exported
  requirements file so CI sees exactly the locked graph.
- Node deps resolve from `pnpm-lock.yaml`; production-only audit fails
  on high/critical advisories. Transitive pins live in
  `pnpm-workspace.yaml` `overrides:` with a comment naming the driving
  advisory; remove them when `next` bumps past the patched versions.
- Scanner set and thresholds: bandit medium+ severity blocks;
  pip-audit blocks on any known CVE in the locked set (initially
  clean); pnpm audit blocks high+ in prod deps; gitleaks blocks on any
  finding outside the challenge-fixture allowlist.
- New vulnerabilities found by the weekly cron must be triaged within
  one week: fix, override-with-comment, or accepted-risk entry above.
- Semgrep and container/IaC scanning are deferred intentionally to keep
  the gate under six minutes; revisit when image publishing starts
  (phase 15).
