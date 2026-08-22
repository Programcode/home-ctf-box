# ADR 0009: Deployment boundaries

Status: accepted

## Context

The plan defines a Community Edition (one host) and a Cluster Edition
(Kubernetes). Packaging must make the safe path the easy path.

## Decision

- Community Edition: Docker Compose profiles (`core`, `dev`,
  `observability`, `workstation`, `legacy-v0`) plus an installer script
  that checks prerequisites, generates secrets, and prints a one-time
  admin setup URL.
- Cluster Edition: a Helm chart with Pod Security (restricted),
  NetworkPolicies, runner node taints, and external PostgreSQL/Redis/
  object storage options. Runner pods request the lab runtime; the
  control plane never holds cluster-admin credentials.
- Public exposure covers only the control plane and gateway/VPN
  endpoints. Lab networks are never published as host ports in any
  profile.
- Images are built multi-arch (amd64/arm64), tagged immutably, and
  referenced by digest in production docs.

## Consequences

- The installer is idempotent and safe to re-run; it never ships
  default credentials.
- Kubernetes-specific features gate on capability detection so the same
  image runs in both editions.
