# Busted Login

Nimbus Corp runs an employee portal on your lab network. The intern who
wrote the sign-in query glued user input straight into a SQL string. You
will prove it from the outside, walk through the bypass, and take the
flag the portal hands to whoever it thinks just authenticated.

## What you will practice

- Reading error output as evidence of string concatenation.
- Writing a tautology payload that closes a quote, adds a true
  condition, and comments out the tail of the query.
- Confirming the result by capturing the per-session flag.

## Scope

Only the portal at `http://target:8000` is in scope. Nothing outside
your lab instance is a target.
