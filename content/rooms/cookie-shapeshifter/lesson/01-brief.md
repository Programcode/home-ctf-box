# Cookie Shapeshifter

Crumb & Co. runs its loyalty portal on a shortcut: whoever you are lives in
a base64 JSON cookie, and the server believes the cookie without checking a
signature. You will decode the profile, see exactly which claim unlocks the
staff counter, re-encode the cookie with that claim changed, and collect
the reward reserved for admins.

## What you will practice

- Reading a base64 JSON session cookie and naming the fields an app trusts.
- Forging a new value for an unsigned cookie.
- Confirming the forge by capturing the per-session flag.

## Scope

Only the portal at `http://target:8000` is in scope. Nothing outside your
lab instance is a target.
