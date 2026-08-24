# Encoding Is Not Encryption

The Meridian Archive runs a training desk for new archivists, and the
first lesson is an uncomfortable one: most of what people call
"encrypted data" is just data wearing a costume. This room walks you
through the costume party so you can see every seam.

You will fetch a sealed blob from the desk's API and peel four layers
off it in reverse order: base64, then hexadecimal, then base64 again,
then rot13. Each layer is a reversible encoding with a recognizable
shape. Base64 uses letters, digits, plus and slash, and pads with equal
signs. Hexadecimal is lowercase digits and letters a through f, two
characters per byte. rot13 shifts every letter thirteen places around
the alphabet and leaves digits and punctuation alone, which is why it
is its own inverse. None of these steps needs a key, and that is the
whole point: anything you can decode without a secret was never
encrypted in the first place.

Alongside the chain you will practice digest identification on real
hashes. A hash takes input of any size and returns a fixed-length
fingerprint that cannot be reversed. You cannot decrypt a hash, but you
can often name its algorithm from shape alone: MD5 prints 32 hex
characters, SHA-1 prints 40, SHA-256 prints 64. The desk serves sample
digests and an identifier endpoint so you can check your eye against a
tool's verdict.

By the end you should be able to say precisely why encoding, hashing,
and encryption are three different jobs, and spot each one in the wild.

## What you will practice

- Peeling layered encodings from the outside in.
- Identifying digest formats by length and character set.
- Arguing why reversible encodings provide zero confidentiality.

## Scope

Only the training desk at `http://target:8000` is in scope. Nothing
outside your lab instance is a target.
