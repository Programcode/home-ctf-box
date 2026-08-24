# Reused Horizon

Horizon Sync sells its telemetry gateway on speed, and the fastest
cipher of all is XOR with a key that never changes. The wire protocol
fixes the frame header, so every install on earth encrypts the same
48 known bytes with the same 32-byte session key. That is not a cipher,
it is a decoder ring waiting for its crib.

In this room you attack the gateway exactly the way cryptanalysts have
attacked reused key streams since the telegraph era. First you pull two
frames from the API: one whose plaintext you already know (the protocol
header, printed in the specification) and one carrying this session's
secret. Because C = P xor K for every byte position, subtracting the
known plaintext from its ciphertext hands you the keystream itself:
K[i] = C2[i] xor P2[i]. No guessing, no brute force, pure arithmetic.

With the keystream in hand the secret frame stops being secret. You XOR
the recovered key across it, wrapping modulo 32 when the frame runs past
one key length, and ASCII text falls out. The exercise teaches the
two-edges-of-one-triangle intuition behind all known-plaintext attacks:
a cipher is only as strong as its freshest key byte, and any byte that
touches two messages belongs to neither.

You will finish able to explain why stream ciphers demand a unique nonce
per message, why "the attacker knows part of the plaintext" is a real
threat model instead of a technicality, and how a single protocol
constant quietly did the attacker's key recovery for them.

## What you will practice

- Recovering a repeating XOR key from a known plaintext pair.
- Decrypting a second message under the same reused key.
- Arguing for per-message nonces in stream cipher designs.

## Scope

Only the gateway at `http://target:8000` is in scope. Nothing outside
your lab instance is a target.
