# ticket-booth

Kerberoasting is the attack that turned ordinary domain users into
offline password crackers: request any service ticket, take it home,
and grind the service account's password at leisure with whatever
hardware you own. The request itself is unremarkable, which is exactly
the problem; every step looks like normal authentication until the
cracking rig starts humming. Real tickets push back through modern
encryption types and long random passwords, but plenty of environments
still run old enctypes with human-chosen secrets, and attackers know
which. This room keeps the entire workflow intact and swaps only the
cipher for a disclosed toy, so every skill from ticket request to
credential reuse gets practiced honestly on data that cannot hurt
anyone. The room also keeps one account uncrackable on purpose, so you
feel the boundary between weak and strong service credentials instead
of reading about it. Documentation comes first in this room, cracking
comes second, and the flag waits behind a real credential check at the
end of both.

## What is real here, and what is simulated

The room is one locked Flask container speaking JSON over plain HTTP.
Its fake KDC registers two SPNs under two fictional service accounts
and issues tickets whose enc-part is base64 over plaintext XORed
against a repeating 32-byte keystream derived from sha256 of the
service-account password. That cipher is deliberately a toy, neither
RC4-HMAC nor AES, and /kdc/docs says so in those words while printing
the exact 48-byte preamble every ticket starts with, because known
plaintext is what makes the offline crack teachable rather than
magical. Determinism is a feature: issued timestamps are fixed, blobs
never change between requests or container restarts, and the crack
always converges on the same answer for the same wordlist, which lets
the grading harness verify your path twice in a row. The provided
getuserspns.py client uses only the Python standard library and speaks
no Kerberos protocol bytes whatsoever. What is genuinely real is the
workflow you rehearse: enumerate SPNs, request tickets, run an offline
dictionary attack against known structure, then reuse what falls out as
working credentials, since the admin console performs actual HTTP Basic
authentication before it shows anything.

## Why service tickets fall

Any authenticated user can ask a key distribution center for a service
ticket, and the KDC grants that request without checking motives,
because asking is a core part of how Windows services authenticate to
each other. The ticket's encrypted part must be verifiable by the
target service alone, so it gets sealed with material derived from the
service account's own password, delivered to whoever asked for it.
Defenders cannot tell an analyst pulling one ticket from an attacker
pulling ten thousand, so the whole attack surface reduces to two
properties: encryption strength and password quality. Modern
environments answer on both fronts by preferring AES enctypes that make
each guess expensive to verify, adopting group-managed service accounts
that remove the shared secret entirely, and generating long random
passwords that starve every wordlist. This room demonstrates the
starvation half directly, since one of its two accounts carries a long
random password that survives the provided list untouched. When you
audit real environments, hunt first for RC4 enctypes paired with
human-chosen passwords; that combination is where kerberoasting still
pays rent.

## Walking the intended path

Read /kdc/docs before touching anything else. The room hands you the
cipher description, the exact preamble bytes, and the crack recipe up
front, because the skill under test is executing the attack loop
cleanly, not reverse engineering a format under time pressure. Download
the client and wordlist from /tools/, then run the client against the
KDC base URL to print each SPN's account name and base64 enc_part.
Decode a blob locally, derive each wordlist candidate's sha256
keystream, XOR the leading ciphertext bytes against it, and test for
the ASCII magic KDCSIM-TGS-V1; the winning candidate reproduces the
entire 48-byte preamble and decrypts the tail into readable SPN text,
which doubles as your correctness check. svc_sql falls to
SQLservice2019 within seconds of starting the loop. svc_web matches
nothing at all, and that silence is the second lesson sitting right
beside the first. Take the recovered credential to /kdc/admin, sign in
with HTTP Basic auth as svc_sql, and the console prints your session
flag once the password verifies.

## Scope

Confine yourself to http://target:8000 within this instance. The
container reaches nothing beyond the lab network: no internet, no host,
no control plane, no neighboring labs. Everything the intended path
needs is published by the box itself: tooling endpoints under /tools/,
the SPN list and ticket issuer under /kdc/, documentation at /kdc/docs,
and one Basic-authenticated console. Do not attempt to extract
passwords or flags from server memory, brute-force the flag alphabet,
flood the ticket endpoint hoping for different keys, or attack the
health endpoint; none of it is necessary and none of it teaches the
technique this room exists to teach. Accounts and credentials printed
anywhere in these rooms are disposable training labels shared across
instances, so never carry them elsewhere, and never point cracking
workflows at systems where you do not hold written authorization to
test. Offline attacks are legal in labs and authorized engagements;
everywhere else they are simply crimes with extra steps.
