# ADR 0002: Licensing split

Status: accepted

## Context

A network learning platform with community contributions needs a license
that keeps forks honest (source availability) while letting training
material spread with attribution.

## Decision

- Platform code: AGPL-3.0-or-later.
- Training content: CC BY-SA 4.0, declared per bundle.

## Consequences

- Commercial self-hosters must share control-plane modifications.
- Content remixing is safe and encouraged with attribution.
- A per-bundle `license` field is mandatory in the content schema so
  exported bundles carry their terms.
