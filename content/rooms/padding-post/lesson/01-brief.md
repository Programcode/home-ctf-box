# Padding Post

Postmaster moves delivery envelopes as AES-CBC ciphertext, and its
integrity desk answers exactly one question about any envelope you
submit: did the padding check out? True or false, nothing more. In 2002
Serge Vaudenay showed that this tiny yes-or-no channel is enough to
decrypt arbitrary ciphertexts without the key, and the attack still
works wherever code treats a padding error differently from other
errors.

This room is the attack in its cleanest form. The service publishes an
envelope whose plaintext starts with a known banner block followed by
the padded flag. You forge two-block queries of your own: a crafted
block R riding in front of each original data block Cn. Because CBC
decryption XORs the previous block into the decrypted data, the oracle's
answer tells you facts about R xor D(Cn). By setting up R so that valid
padding can only mean "the final decrypted byte equals 0x01", you learn
one byte of D(Cn) with at most 256 guesses; then you shift the padding
expectation one position left and repeat. Each recovered intermediate
byte turns into real plaintext through P = D xor Cprev.

Expect a few thousand requests. The endpoint is deliberately not rate
limited so you can watch the side channel breathe, and the solver
pattern here (persistent connection, systematic byte sweep, a flip test
to reject lucky false positives) mirrors how real padding oracle
exploits behave against production services. When your recovered banner
reads PADDINGPOST-V1:: back to you, the math is right, and the flag
blocks will already be sitting next to it.

By the end you should be able to explain why MAC-then-encrypt failed,
why encrypt-then-MAC or AEAD closes this hole, and why a boolean leak
counts as a decryption capability.

## What you will practice

- Forging CBC ciphertext pairs that interrogate one decrypted byte at a time.
- Running the full byte-at-a-time oracle loop, including false positive handling.
- Connecting the exercise to real historical vulnerabilities such as TLS POODLE-era flaws and ASP.NET padding oracles.

## Scope

Only the delivery API at `http://target:8000` is in scope. Nothing
outside your lab instance is a target.
