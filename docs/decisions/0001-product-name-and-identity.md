# ADR 0001: Product name and identity

Status: accepted (working title, final choice pending Adam)

## Context

The platform needs a name distinct from Hack The Box, TryHackMe, and
every other training vendor. The repository is `home-ctf-box`, which
describes the origin but not the product. The final public name is one
of the human decisions listed in the implementation plan (section 15).

## Decision

Use **OpenRange** as the working title in code, docs, and UI copy. The
content CLI keeps the plan-specified name `cyberrange`. Mark both as
provisional; a rename before first public release touches branding
strings only, not schemas or APIs.

## Consequences

- No trademark search has been done yet. Before any public release,
  search "OpenRange" for conflicts and pick a final name.
- All user-facing strings come from one theme file so a rename stays
  mechanical.
