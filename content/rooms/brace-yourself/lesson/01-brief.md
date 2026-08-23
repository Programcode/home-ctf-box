# Brace Yourself

The portal builds its greeting by gluing your name parameter into a
template string, then running str.format over the whole thing with
server-side context as keyword arguments. Fields in braces get filled
in, including ones you were never supposed to see.

## What you will practice

- Spotting the fingerprint of str.format on a page: values appear that
  you never typed.
- Submitting input that is itself a placeholder for hidden context.
- Reading the flag from the rendered greeting.

## Scope

Only the portal at `http://target:8000` is in scope. Nothing outside
your lab instance is a target.
