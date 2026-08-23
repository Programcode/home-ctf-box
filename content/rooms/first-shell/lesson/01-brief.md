# First Shell

Every shell room starts the same way: get a session, look around, take
what the scenario says is yours. This box runs a stock SSH server on
your lab network. The login banner hands you a low-privilege account,
and the objective sits in that account's own home directory, readable
because the file belongs to you.

## What you will practice

- Starting an SSH session from the terminal with a password.
- Confirming who and where you are with whoami, pwd, and ls -la.
- Reading a file you own and recognizing the per-session flag format.

## Scope

Only the box at `ssh://target:22` is in scope. Nothing outside your
lab instance is a target, and the lab account has no special powers on
purpose: this room is about the basics, not escalation.
