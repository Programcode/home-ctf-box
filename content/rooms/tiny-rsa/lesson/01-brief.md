# Tiny RSA

RSA's security story rests on one inequality: the message, raised to
the public exponent, must wrap around the modulus so many times that no
root finds its way back. FastSign's TinyVault breaks that story in
three separate places at once. The modulus is a slim 512 bits, chosen
for speed. The exponent is e=3, the smallest value RSA allows. And the
padding is a row of zero bytes instead of a randomized OAEP scheme.

The consequence is arithmetic you can do on paper. Each sealed chunk
fits in 16 bytes, so the message integer m is smaller than 2^128.
Cubing gives m^3 < 2^384, while the modulus n sits above 2^511. The
reduction mod n never fires, so every ciphertext block is not "m cubed
mod something", it is exactly m cubed, an ordinary perfect cube over
the integers. Recovering m means taking a cube root, which Python does
with a dozen lines of binary search and no crypto library at all.

This room walks you through that attack end to end: pulling the public
parameters and sealed blocks from the API, verifying for yourself that
each ciphertext is a perfect cube, writing your own integer cube-root
routine, and reassembling the chunks into plaintext. Along the way you
will see precisely what randomized padding buys. OAEP embeds the
message with random seeds before exponentiation, pushing it near the
modulus size and destroying any clean algebraic structure; zero padding
keeps the message tiny and leaves the cube sitting in plain sight.

By the end you should be able to state the small-exponent attack
conditions from memory, explain why textbook RSA fails both
confidentiality and indistinguishability tests, and argue for OAEP as
standard practice rather than optional polish.

## What you will practice

- Verifying the size bound that makes modular reduction inert.
- Implementing integer nth roots with plain Python integers.
- Explaining the role of randomized padding in modern RSA.

## Scope

Only the sealing desk at `http://target:8000` is in scope. Nothing
outside your lab instance is a target.
