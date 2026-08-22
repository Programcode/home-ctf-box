# ADR 0004: Single-node and cluster parity

Status: accepted

## Context

The platform must run on one Linux box (or a Raspberry Pi 5) for a home
lab, and on a Kubernetes cluster for a serious installation. Divergent
code paths per deployment would double maintenance and split the
community.

## Decision

One control plane codebase. Deployment differences live behind two
interfaces:

- a `LabProvider` interface with a Docker/Podman implementation
  (single-node) and a Kubernetes implementation (cluster);
- configuration profiles that scale concurrency, workers, and storage.

Both editions expose identical APIs and consume identical content
bundles. Features that cannot work on constrained hardware (VM labs,
Windows/AD) degrade by capability advertisement, not by forks: the
catalog hides content whose runtime requirements the installation does
not meet, with an explanation.

## Consequences

- Every feature PR must state its behavior in both editions.
- Capability discovery (`/api/system/capabilities`) drives UI gating.
