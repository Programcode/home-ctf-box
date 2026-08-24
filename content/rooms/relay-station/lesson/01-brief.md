# relay-station

Relay attacks live in the gap between what a credential proves and
who it was meant for. A challenge-response handshake proves the
account knows the secret, but unless something ties that proof to the
specific connection it belongs to, whoever carries the pieces can
finish someone else's login. NTLM made this famous because its
responses are exactly such loose credentials, and whole toolchains
exist to trick machines into authenticating toward attackers who
forward the exchange elsewhere. This room rebuilds that idea with no
NTLM at all: a coordinator mints challenges per target, a printer
device answers whatever challenge you present under its account, and a
fileserver endpoint accepts proofs computed for its own challenge.
Your job is to be the middle: capture the right challenge, get the
printer to answer it, and deliver the answer where it opens doors.
Every formula you need is published inside the room, so the exercise
stays honest; what you are practicing is the carrying, not the math.

## What is real here, and what is simulated

The room is one locked Flask container speaking JSON over plain HTTP.
Its coordinator derives each challenge deterministically as
sha256("challenge|<target>|COORDSIM-RELAY-V1") truncated to 24 hex
characters, and devices answer with HMAC-SHA256 keyed by sha256 of the
account password over the challenge bytes. Both formulas sit on
/docs/protocol in plain language. That scheme is deliberately a toy
standing in for NTLMv2; there is no SMB, no NTLM negotiation, no
Net-NTLM hash material worth the name, and responder-style sniffing
has nothing to sniff here. All accounts are fictional training labels,
the password never leaves the device endpoint, and determinism means
identical requests produce identical challenges and proofs across
container restarts so the grading harness can verify your path twice.
What is genuinely real is the structural lesson the simulation keeps
intact: the proof is bound only to its challenge bytes, never to the
session or channel that requested them, and /fileserver/verify
enforces exactly one check, that the challenge matches what fileserver
itself would mint. The negative control shows the boundary honestly:
proofs answering a printserver challenge fail with
WRONG_TARGET_CHALLENGE rather than succeeding by luck.

## Why relaying works until binding closes it

Three properties make relay possible in real networks. Authentication
material must survive being carried somewhere else, which challenge
response satisfies since the proof stays valid for minutes. The client
must not verify whom it is talking to, which holds whenever signing
and channel binding stay off. And the target must accept forwarded
handshakes, which NTLM does by default on countless legacy servers.
Attackers combine coercion with relay: printer bugs or similar
triggers make a machine account authenticate toward them, then the
exchange gets forwarded to whichever juicy service still permits NTLM.
Defenders shrink this surface with three moves that map directly onto
this room's controls. Enable SMB signing and EPA so tampered or
forwarded sessions die at negotiation. Restrict inbound NTLM through
policy so modern clients negotiate Kerberos instead. And monitor
coercion indicators like unexpected machine-account authentication
toward workstations. When those land, the exact flow this room teaches
collapses at every step.

## Walking the intended path

Read /docs/protocol first; every formula is printed there, including
the room secret, because nothing here needs guessing. The provided
client at /tools/relay-sim.py chains all four steps and prints its
work, which makes it the fastest route. It fetches GET
/coordinator/challenge?target=fileserver, presents that hex value to
POST /devices/printer/connect, receives {account, answered_challenge,
proof}, demonstrates the negative control against a printserver
challenge, then relays the captured triple to POST /fileserver/verify
with account, challenge, and proof fields. The final page verifies the
HMAC, confirms the challenge is the fileserver one, and prints
FLAG{...}. Submit that value. If you prefer doing it by hand with curl
or httpx, each step maps to one request and the protocol page gives
you everything needed to predict responses before sending them. Watch
what the device endpoint does NOT do: it never asks who you are or
where the challenge came from, and that absence is precisely the
misconfiguration class defenders close with channel binding.

## Scope

Confine yourself to http://target:8000 within this instance. The
container reaches nothing beyond the lab network: no internet, no
host, no control plane, no neighboring labs. Everything the intended
path needs is published by the box itself: challenges, device
endpoints, verification, documentation, and the client tool. Do not
attempt to recover the printer password from HMAC outputs, brute-force
flag material, flood endpoints, or attack the health check; none of it
is necessary and none of it teaches the technique this room exists to
teach, and the HMAC construction gives nothing back to a guesser
anyway since every output is indistinguishable from random until the
right password shows up.
Real-world relay against systems you lack written authorization
to test is a crime regardless of how educational the intent feels;
labs like this exist so the practice stays legal. Credentials shown
here are disposable training labels shared across instances, so never
carry them anywhere else, and treat any captured authentication
material you meet in production as incident evidence, not a curiosity.
