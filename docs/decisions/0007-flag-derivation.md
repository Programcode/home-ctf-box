# ADR 0007: Per-session flag derivation

Status: accepted

## Context

Static flags baked into images leak through screenshots, writeups, and
image sharing, and they let one learner's solve validate for everyone.
The platform needs flags unique to a user (or team/event session) that
cannot be pre-shared, while keeping validation fast.

## Decision

Flags are derived, not stored per user:

```
flag = FLAG{ base32( HMAC-SHA256( master_key,
         scope || user_or_team_id || lab_instance_id || content_id || task_id ) ) }
```

- `master_key` is a deployment secret, rotatable; derivation includes a
  key version so old flags stay valid until their labs expire.
- The runner injects the derived flag into the instance at start
  (environment/file, per the room's flag delivery declaration).
- The API validates submissions by recomputing the expected value for
  the caller's active instance. Where a room cannot render a dynamic
  flag, the bundle may declare a static validator that stores only a
  hash, and the review gate must approve the exception.

## Consequences

- Sharing a flag string outside the instance is useless.
- Score attribution is provable: a correct flag implies the caller had a
  live instance for that content.
- Key rotation must respect running leases; rotation docs cover the
  dual-key window.
