# ADR 0006: Content packaging format

Status: accepted

## Context

Content must be authored in git, validated in CI, previewed locally,
published through review, and rendered by the API without application
code changes. Competitor platforms lock authoring into a web studio; we
want git-native workflows with the studio as a convenience layer.

## Decision

A room/module/path is a directory bundle:

- `room.yaml` (or `module.yaml`, `path.yaml`): metadata, objectives,
  prerequisites, difficulty, tasks/questions/hints/solutions,
  target topology, licensing, safety declaration.
- `lesson/`: Markdown sections with a strict renderer allowlist.
- `target/`: Dockerfile plus healthcheck for lab-backed rooms.
- `solver/`: Python package with `solve(ctx)` implementing the
  intended path end to end.
- `tests/`: reset/idempotency and unintended-shortcut checks.

The `cyberrange` CLI (`new|lint|build|preview|solve|test|pack|publish`)
is the only supported authoring entry point. The API ingests built,
versioned bundles; it never imports room logic at runtime beyond the
declared validator types.

## Consequences

- Adding a room is a data change, reviewable as a diff.
- The validator type system must cover common cases (exact, normalized,
  regex with timeout, numeric range, set, per-session flag, file hash,
  manual review) so arbitrary code does not run in the control plane.
- Solver execution happens in the content CI stage against disposable
  containers, not in the production API.
