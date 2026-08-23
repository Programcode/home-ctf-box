# Trusted Proxy

Gatehouse keeps an internal panel behind an address check, but the check
asks a request header where the caller lives before it looks at the
actual connection. You will see how the decision is made, override it
with a forged header, and read what the panel shows office callers.

## What you will practice

- Reading access-control code that trusts client-supplied headers.
- Forging X-Forwarded-For to impersonate a trusted source.
- Confirming the bypass by capturing the per-session flag.

## Scope

Only the gate at `http://target:8000` is in scope. Nothing outside your
lab instance is a target.
