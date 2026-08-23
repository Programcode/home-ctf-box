# sudo-side-door

Sudo grants are usually written with one task in mind and read with no
imagination at all. This box lets the learner account run /usr/bin/find
as root without a password, which sounded harmless when it was written.
find has an -exec action that runs a command of your choice on every
path it matches. The grant names the tool; you choose what the tool
does.

## What you will practice

- Reading your own sudo policy with sudo -l and tracing where a
  drop-in grant comes from.
- Thinking about binaries as combinations of capabilities instead of
  single purposes.
- Turning find's file-walking into a controlled root command.

## Scope

Only the box at `ssh://target:22` is in scope. Nothing outside your lab
instance is a target. The intended abuse is a single read of this
container's own flag file, nothing more.
