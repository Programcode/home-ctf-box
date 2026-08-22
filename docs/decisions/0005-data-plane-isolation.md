# ADR 0005: Untrusted data-plane isolation

Status: accepted

## Context

Room targets are intentionally vulnerable and attacker-controlled. A
compromised lab must not reach the host, the control plane, other
tenants, or the internet.

## Decision

Treat every lab container as hostile:

- Per-instance Docker networks. No shared lab bridge.
- Default-deny egress; per-room allowlists for required destinations;
  block RFC1918 control-plane ranges, host gateway, cloud metadata
  (169.254.169.254), and DNS rebinding names.
- Containers run non-root, no-new-privileges, dropped capabilities,
  seccomp default profile, read-only root filesystem where the room
  permits, CPU/memory/PID/disk quotas, and a TTL lease.
- The Docker socket is mounted only in the runner agent service, never
  in web/API/worker containers. The runner exposes a narrow
  HMAC-authenticated operation API.
- Host mounts are denied except an explicit per-room allowlist of
  tmpfs-style paths inside the instance namespace.

## Consequences

- Some techniques (kernel exploits, raw sockets) need capabilities the
  defaults deny; such rooms declare their requirements and are gated by
  capability advertisement plus review approval, never enabled globally.
- Egress allowlists make package installation at runtime unreliable;
  rooms bake tooling into images instead.
