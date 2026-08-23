# Token Forger

TokenForge signs session tokens with HS256, yet its verifier lets each
token name the algorithm it should be checked with. You will log in as
a guest, take the issued token apart, and forge one that opens the
admin console without knowing the signing key.

## What you will practice

- Reading a JWT's three base64url segments and changing their contents.
- Spotting the alg:none trust flaw in hand-rolled verification code.
- Forging an unsigned token with role=admin and presenting it to the
  admin endpoint.

## Scope

Only TokenForge at `http://target:8000` is in scope. Nothing outside
your lab instance is a target.
