# ADR 0003: Web and API stack

Status: accepted

## Context

The platform needs a rich, accessible learner UI, a typed API contract,
background workers, and a content toolchain. The team of maintainers is
small; the ecosystem choices must be boring and well-trodden.

## Decision

- Web: Next.js (App Router) + TypeScript + Tailwind, with a local
  design-system package instead of a heavy component vendor.
- API: FastAPI + SQLAlchemy 2 (async) + Alembic on PostgreSQL.
- Workers: Celery on Redis.
- Contract: OpenAPI generated from FastAPI; TypeScript client generated
  into `packages/contracts`; Python side uses Pydantic models as the
  single source.
- Search: Meilisearch. Storage: S3-compatible (MinIO locally).

## Consequences

- Two languages, one contract: the OpenAPI document is authoritative
  and CI fails when the committed client is stale.
- Async SQLAlchemy adds ceremony but matches FastAPI's model and keeps
  long lab operations from blocking the event loop.
