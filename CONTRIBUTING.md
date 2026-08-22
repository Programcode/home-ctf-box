# Contributing

Thanks for helping build an open cyber range. This document covers how
work lands in the repository.

## What the project needs

- platform code: API (Python/FastAPI), web (TypeScript/Next.js),
  worker, gateway, runner;
- content: rooms, modules, paths, authored as declarative bundles under
  `content/` with automated solvers and tests;
- reviews: technical, instructional, and security review of content;
- ops: CI, packaging, docs.

## Ground rules

1. Code is AGPL-3.0-or-later. Original prose and assets are CC BY-SA
   4.0. Never copy proprietary platform content, branding, flags, or
   solutions from commercial training sites.
2. Vulnerable targets stay inside lab scope. No real malware binaries
   in the repository; offensive technique rooms use purpose-built,
   inert simulations.
3. Every room ships with a working intended-path solver and tests. A
   bundle that fails `cyberrange content lint` or its solver test does
   not merge.

## Workflow

- Branch from `main`, name it `feat/...`, `fix/...`, `docs/...`,
  `content/...`.
- Commits follow Conventional Commits (`feat(api): ...`,
  `content(rooms): ...`). The changelog is generated from commit
  messages.
- One logical change per pull request. CI must be green before review
  counts.
- Content changes need at least one technical review and one
  instructional review before publish. Authors cannot approve their own
  public content (single-admin installs can disable this locally).

## Local setup

```sh
make bootstrap   # installs Python (uv) and Node (pnpm) toolchains
make check       # lint + typecheck everything
make test-unit   # fast unit tests
```

See `docs/` for architecture, authoring, and operator guides. The plan
of record lives at `.hermes/plans/`; current status is tracked in
`docs/roadmap/implementation-status.md`.

## Review expectations

Reviewers check correctness first, then safety (scope, egress, flag
handling), then instructional quality (objectives, hints, solution).
"Works on my machine" is not verification; point to the test run or the
solver output.
