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

## Phases 1–15

All `not-started`. Each phase gets its own section with per-task status
as work begins.

## Human decisions pending (plan section 15)

These block public release only, not local implementation:

1. Final product name and identity (working title: OpenRange).
2. License confirmation (AGPL-3.0 + CC BY-SA 4.0 recommended).
3. Public domain, email/OAuth providers, telemetry/moderation policy.
4. Hardware/budget for clustered runners and licensed Windows images.
5. Whether community content/events ship enabled on first hosted instance.
6. External security review before claiming internet-ready cluster mode.
