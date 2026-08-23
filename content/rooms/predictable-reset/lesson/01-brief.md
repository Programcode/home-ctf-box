# Predictable Reset

ResetFlow is a password reset portal that mints a fresh link every 10
minutes. That expiry window is the only hint you get, and it is enough:
the token behind each link is derived from the username and the clock
alone. You will request a reset, rebuild the token on your own machine,
and collect the credentials the service prints for whoever presents it.

## What you will practice

- Reading product copy for evidence of how security tokens are built.
- Recomputing a server-side digest offline when no secret is mixed in.
- Confirming the forgery by capturing the per-session flag.

## Scope

Only the portal at `http://target:8000` is in scope. Nothing outside
your lab instance is a target.
