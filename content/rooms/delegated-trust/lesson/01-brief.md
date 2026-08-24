# delegated-trust

Delegation is the domain's way of saying one service may act as
someone else, and constrained delegation is the attempt to keep that
sentence short and specific. The mechanism exists for real reasons:
web servers need to reach back-end databases as the actual user, not
as themselves. But the power lives wherever the service account does,
so whoever controls svc_web controls every identity svc_web is allowed
to become. Compromise the service once and the domain hands you a
ticket factory for more privileged principals. This room walks the
whole arc on training data: find the leaked credential from an earlier
phase, read the delegation configuration to learn whose identity is
within reach, mint the impersonation token, then spend it where only
administrators are welcome. Nothing about the flow is hidden from you,
which is the point; in production the hard part is never the protocol
choreography, it is noticing that the allowlist exists at all and
asking who else already satisfies its front door.

## What is real here, and what is simulated

The room is one locked Flask container speaking JSON over plain HTTP.
Its fake domain controller tracks two fictional service accounts and
publishes their msDS-AllowedToDelegateTo equivalent at
/delegation/config. The simulated S4U flow mints tokens of the form
S4USIM.v1.<base64url payload>.<hex HMAC>, signed with HMAC-SHA256
under a fixed room secret printed in full on /dc/docs; that signature
scheme is deliberately a toy standing in for PAC-bearing Kerberos
service tickets, chosen for determinism and legality, and nothing
anywhere speaks Kerberos protocol bytes. Determinism matters: the same
request always yields the same token across restarts, so the grading
harness can verify your path twice in a row. What is genuinely real is
the workflow and its guardrails. The recon leak is staged text inside
this container, but reading it, choosing the right target from the
allowlist, presenting service credentials, and carrying a verified
token to a protected endpoint rehearse exactly the decisions a real
engagement demands. /tgs rejects any impersonation target outside the
configured list with DELEGATION_NOT_PERMITTED, mirroring how a real
KDC enforces delegation bounds per hop.

## Why delegated rights concentrate risk

Protocol transition exists because services legitimately need to
present themselves as their callers. S4U2Self lets a service ask the
domain controller for a ticket to itself claiming some other
principal, no password required, and S4U2Proxy lets it exchange that
ticket for access to a downstream service. Each hop checks the
msDS-AllowedToDelegateTo list, which is why defenders describe
constrained delegation as safe when configured tightly. The failure
mode is arithmetic: any account allowed to delegate to administrator
is worth exactly as much as administrator to whoever owns it, and
service accounts rarely get the monitoring that human admins get.
Attack chains therefore run through whatever leaks service credentials,
config backups, SYSVOL scripts, command lines visible in process
lists, and land on the delegation list as the multiplier. Defenders
respond by keeping allowlists minimal, avoiding high-value targets on
them entirely, preferring resource-based constrained delegation scoped
by the receiving side, and rotating service credentials so yesterday's
leak stops mattering tomorrow.

## Walking the intended path

Read /dc/docs first: token format, signing scheme, and disclosure sit
there in plain language. GET /recon/index lists artifacts left by a
fictional earlier phase; /recon/files/web-config.bak holds a
connection string containing uid=svc_web;pwd=WebDeleg@te26. That
credential pattern, secrets sitting in config backups, causes more
delegation compromises than any protocol flaw. GET /delegation/config
shows svc_web carries SPN HTTP/dc01.lab.local and may impersonate
administrator, while svc_print's empty list answers 403 for anything.
GET /tgs?impersonate=administrator with Basic auth as svc_web returns
the S4USIM token. Present it to GET /dc/admin-only as a Bearer header;
the page verifies the HMAC, reads impersonate=administrator from the
verified payload, and prints your session flag. Try the negative path
too, requesting impersonation of some other principal, and watch the
allowlist refuse; the refusal is the control this room exists to teach
about sizing correctly. One more exercise costs nothing and pays well:
decode the token payload and confirm for yourself that the identity
lives in readable data once the signature verifies, since every
downstream control in a real deployment depends on that verification
existing and being enforced.

## Scope

Confine yourself to http://target:8000 within this instance. The
container reaches nothing beyond the lab network: no internet, no
host, no control plane, no neighboring labs. Everything the intended
path needs is published by the box itself: recon artifacts under
/recon/, configuration under /delegation/config, the token issuer
under /tgs, documentation at /dc/docs, and one protected resource. Do
not attempt to brute-force the room secret, forge tokens offline
against the flag alphabet, flood the token endpoint, or attack the
health endpoint; none of it is necessary and none of it teaches the
technique this room exists to teach. The room secret is printed on the
docs page on purpose, so there is nothing to guess and no glory in
trying. Accounts and credentials printed anywhere in these rooms are
disposable training labels shared across instances, so never carry
them elsewhere. Delegation abuse without written authorization is
intrusion, full stop; practice it only where the owner signed off
first.
