# as-rep-arcade

Pre-authentication is the Kerberos handshake that forces a requester
to prove an identity before the domain controller will hand over any
encrypted material. Turn it off, usually for some legacy application
that never learned the modern dance, and the controller answers the
first request with an AS-REP whose encrypted part is keyed by the
account's own password. Anyone on the network can ask for it, and once
it arrives the account's password quality becomes the only thing
standing between you and the credential. This room rebuilds that arc
on honest training data: enumerate who lacks pre-auth, request their
material, grind a wordlist against it offline, then use what falls out
as a real credential somewhere else. One weak password falls, one long
random password refuses to, and both outcomes are part of the lesson.
The mechanics stay simple on purpose, so your attention lands on the
decision chain rather than on protocol trivia: what got listed, what
got requested, what cracked, and where the result was accepted.

## What is real here, and what is simulated

The room is one locked Flask container speaking JSON over plain HTTP.
Its fake KDC tracks four fictional accounts, two of them flagged as
having pre-authentication disabled, and issues enc-parts computed by
XORing plaintext against a repeating 32-byte keystream taken from
sha256 of the account password. That cipher is deliberately a toy,
neither RC4-HMAC nor AES, and /kdc/docs says so in those words while
printing the exact 16-byte preamble every enc-part starts with.
Determinism is a feature: issued timestamps are fixed, blobs never
change between requests or container restarts, and the crack always
converges on the same answer for the same wordlist, which lets the
grading harness verify your path twice in a row. The provided
getasreproast.py client uses only the Python standard library and
speaks no Kerberos protocol bytes whatsoever. What is genuinely real
is the workflow: enumeration through /users?no-preauth=1, ticket
requests, an offline dictionary attack against known structure, and a
credential check at /redeem that actually compares your submission
against the stored secret before it shows anything.

## Why missing pre-auth leaks offline material

With pre-auth enabled, a requester must first send a timestamp sealed
under their own key, and only then does the controller reply with
anything encrypted. Disable it and the ordering collapses: the server
hands over the encrypted blob to whoever asks, no proof required. The
attacker no longer needs to guess against a login endpoint with lockout
policies and logging; they take one blob home and test guesses at full
cracking speed with zero network noise. Defenders close this by
auditing for accounts with pre-auth disabled, fixing or retiring them,
and making sure whatever survives carries long random passwords that
starve every wordlist. The room demonstrates both halves directly:
svc_archive falls within seconds because ArchiveIt92 sits in the
published list, while svc_audit leaks its enc-part just as freely and
still cannot be cracked because its random password is absent from the
list on purpose. When you audit real environments, DsHeuristics and
the UF_DONT_REQUIRE_PREAUTH flag are the two places to look; either
one turning up on a service account is a finding worth writing.

## Walking the intended path

Read /kdc/docs before touching anything else. The room hands you the
cipher description, the exact preamble bytes, and the crack recipe up
front, because the skill under test is executing the attack loop
cleanly, not reverse engineering a format under time pressure. Save
the client and wordlist from /tools/, run the client against the KDC
base URL, and it prints each vulnerable account with its base64
enc-part while normal accounts answer PREAUTH_REQUIRED, which is the
protection doing its job. Decode a blob locally, derive each wordlist
candidate's sha256 keystream, XOR the leading ciphertext bytes against
it, and test for the ASCII magic ASREPSIM-V1; the winning candidate
reproduces the entire preamble and decrypts the tail into readable
user text, which doubles as your correctness check. svc_archive yields
ArchiveIt92 almost immediately. svc_audit matches nothing at all, and
that silence is the second lesson sitting right beside the first. Take
the recovered credential to POST /redeem as JSON with username and
password fields, and the confirmation page prints your session flag
once the password verifies.

## Scope

Confine yourself to http://target:8000 within this instance. The
container reaches nothing beyond the lab network: no internet, no host,
no control plane, no neighboring labs. Everything the intended path
needs is published by the box itself: the user listing under /users,
the enc-part issuer under /kdc/as, documentation at /kdc/docs, tooling
endpoints under /tools/, and one redeem endpoint. Do not attempt to
extract passwords from server memory, brute-force the flag alphabet,
flood the AS endpoint hoping for different keys, or attack the health
endpoint; none of it is necessary and none of it teaches the technique
this room exists to teach. Accounts and credentials printed anywhere in
these rooms are disposable training labels shared across instances, so
never carry them elsewhere, and never point cracking workflows at
systems where you do not hold written authorization to test. Offline
attacks are legal in labs and authorized engagements; everywhere else
they are simply crimes with extra steps.
