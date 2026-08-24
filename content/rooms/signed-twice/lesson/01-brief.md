# Signed Twice

Digital signatures keep a secret alive only as long as every signature
uses a different random nonce. LedgerLine's audit signer breaks that
rule in public. The service signs ledger entries with DSA over small,
fully documented fields (512-bit p, 160-bit q, SHA-256 truncated to its
leftmost 160 bits), and today's transparency feed at /api/audit shows
two entries whose signatures carry the same r value. In DSA, r depends
only on the nonce k, so identical r is the signer confessing, in
public, that it reused its secret randomness.

The rest is algebra anyone can run. Each signature satisfies s = k^-1
(z + x r) mod q with the same unknowns: nonce k and private key x. Two
equations, two unknowns. Subtract them and x cancels out, leaving
k = (z1 - z2)(s1 - s2)^-1 mod q, computable with Python's pow(a, -1, q)
and nothing else. Feed k back into one equation and the private key x
falls out; checking pow(g, x, p) against the published y confirms you
hold svc-admin's actual signing capability.

With the private key recovered, the admin token desk stops being an
obstacle. You hash your own token string per the posted spec, pick any
fresh nonce, compute r and s exactly as the service does, and post
them as decimal form fields. The verifier does all the work of proving
you are svc-admin.

This room is the honest version of attacks that emptied real wallets:
the 2010 Sony PS3 code-signing failure and Android Bitcoin wallet drains
both came from exactly this arithmetic. You will leave able to detect
nonce reuse from signatures alone, explain why deterministic nonces
(RFC 6979 style) or proper CSPRNG draws matter, and never again accept
"random-looking numbers" as evidence of security.

## What you will practice

- Reading repeated r values as proof of nonce reuse.
- Recovering DSA nonces and private keys with modular inverses.
- Producing valid signatures over attacker-chosen messages.

## Scope

Only the audit signer at `http://target:8000` is in scope. Nothing
outside your lab instance is a target.
