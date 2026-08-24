# certificate-misprint

Certificate templates are where Active Directory decides who is
allowed to become whom. Most of the time the subject name comes from
the requester's own identity, so a certificate is just proof of
yourself. Flip one flag and let the enrollee type in whatever subject
alternative name they like, leave enrollment open to ordinary domain
users, and let the result authenticate, and the certificate authority
will happily print credentials for administrator on request. That combination is ESC1, the most famous entry in a whole family of AD CS
misconfigurations, and it survives in production environments because
templates get copied from old servers nobody remembers commissioning,
then trusted simply because they have always been there.
This room rebuilds the flaw end to end: read the templates, find the
one that accepts caller-supplied SANs, enroll as the low-privilege lab
user asking to be administrator, then present what came back and watch
the signature check pass.

## What is real here, and what is simulated

The room is one locked Flask container speaking JSON over plain HTTP.
Its fake CA tracks two templates and signs certificates as toy RSA:
SHA-256 digest of a canonical field string raised to d mod n with
documented 512-bit keys hardcoded in app.py. There is no X.509, no
padding scheme, no Kerberos PKINIT, and /ca/docs discloses every one
of those choices while publishing the public key at /ca/pubkey for
independent verification. The keys are small enough to print in source
and exist only inside this container; that is the point of calling it
a misprint rather than a certificate. Determinism is preserved by
deriving serial numbers from the signed fields, so the same enrollment
yields byte-identical output across restarts and the grading harness
can verify your path twice in a row. What is genuinely real is the
authorization logic: the enrollment endpoint checks template policy,
refuses caller-supplied SANs wherever san_from_request is false, and
the admin page re-verifies signatures before reading identity out of
the verified payload, never trusting the header alone.

## Why a SAN checkbox equals identity forgery

A certificate means whatever the relying party reads from it. When a
service authenticates a principal from a cert, it takes the identity
from the SAN, not from the keyholder's enrollment account. The CA only
vouches that it issued the blob; whether the requested SAN was
legitimate was decided at enrollment time by the template. So the
security question collapses into three flags: who may enroll, does the
enrollee supply the subject, and can the resulting cert authenticate.
ESC1 answers yes to all three. Defenders audit templates for exactly
this shape using tools like Locksmith or Certipy in report mode, close
enrollment rights down to specific groups, clear
ENROLLEE_SUPPLIES_SUBJECT wherever it has no documented reason to
exist, and mark authentication-capable templates as managers-approve
when in doubt. The room shows both sides of the boundary directly:
UserAuth-Signing rejects your SAN parameter with SAN_NOT_ALLOWED while
WebEnroll-2023 accepts administrator without blinking, same user, same
request, different template setting.

## Walking the intended path

Read /ca/docs first: scheme, key sizes, disclosure, all written there.
GET /ca/templates shows UserAuth-Signing with san_from_request false
and WebEnroll-2023 with it true. POST /ca/enroll with JSON body
{"template": "WebEnroll-2023", "san": "administrator"} under Basic auth
labuser and LabEnroll2026!. The response carries serial, subject
CN=labuser, san administrator, template name, hex sig, and a base64
cert_token. Decode it and notice what happened: subject stayed you
while SAN became someone else, which is precisely why defenders must
watch template flags rather than issuance logs. Optionally fetch
/ca/pubkey and verify the signature yourself; the arithmetic is three
lines. GET /admin with header X-Client-Cert-SIM set to the token. The
server verifies pow(sig,e,n) against the published modulus, requires
san equal to administrator, and prints FLAG{...}. Submit that value.
For contrast, replay the same token against a modified SAN field and
watch verification fail; the signature covers the SAN, which is why
tampering needs a new enrollment instead of an edit.

## Scope

Confine yourself to http://target:8000 within this instance. The
container reaches nothing beyond the lab network: no internet, no
host, no control plane, no neighboring labs. Everything the intended
path needs is published by the box itself: templates, docs, public
key, enrollment, and one protected page. Do not attempt to factor the
modulus, brute-force flag material, flood enrollment, or attack the
health endpoint; none of it is necessary and none of it teaches the
technique this room exists to teach. The private key is hardcoded in
this container's source and protects nothing beyond it, but treat that
habit seriously anyway: real engagement work means touching CAs whose
keys matter enormously, so practice only where authorization is
written down first. Accounts and credentials in these rooms are
disposable training labels shared across instances; never carry them
elsewhere, and never assume a lab template setting says anything about
a production one until you have looked.
