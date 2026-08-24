# Role Play

Cloud breaches rarely announce themselves with a broken door. They
walk in through permissions that each look reasonable in isolation.
A developer may invoke one reporting function. The same developer may
hand one specific role to compute resources, because deployment
automation once needed it. Neither grant raises an eyebrow until you
ask what happens when they are used together, and that question is
the entire discipline of IAM escalation analysis. Security teams
spend most of their cloud-hardening budget on obvious things,
networks and encryption and patching, while the quiet composition of
ordinary grants does the damage. Post-incident reports across the
industry keep describing the same shape: no malware, no exploit, just
an identity whose two permissions summed to something neither author
intended. This room reproduces that shape at toy scale so you learn
to see it before a real attacker demonstrates it for you. The console
you will use publishes every policy document openly, because the
audit half of the skill depends on reading grants precisely rather
than guessing at them.

## What is real here, and what is simulated

The console on port 8000 is a single Flask process pretending to be a
cloud identity plane, and it admits it on the landing page. Users,
roles, functions, and policies are static dictionaries; context
tokens are sha256 digests of the function and role names, so they are
deterministic and carry no real credentials; nothing leaves the lab
network. What is faithful is the evaluation model. Policy documents
are JSON statements of effect, action, and resource, exactly the
grammar you audit in real accounts. Invoking without passing a role
runs in a sandbox baseline, mirroring how a function does nothing
privileged by itself. Passing a role requires both lambda:InvokeFunction
on the target and iam:PassRole on the role, because that conjunction
is how real platforms reason about handing identities to compute. A
read-only decoy user, a function nobody may invoke, and a hard Deny
on direct role assumption give you wrong turns worth understanding
before the right one clicks.

## Reading policies as a system

Open /iam/users/dev-cli before touching anything else. Three
statements tell a complete story. The first allows invoking nightly-
report, scoped to its exact ARN. The second allows iam:PassRole on
report-runner, equally narrow. The third denies sts:AssumeRole on
everything, closing the obvious path. Auditors learn to read such
documents pairwise: any identity holding both invoke over some
function and pass over some role controls what that compute can do,
regardless of what the user itself could never do alone. Check what
the role can do next via /iam/roles/report-runner, and the ladder
reveals itself: report-runner may invoke admin-console while passing
admin-role. Two rungs of the same pattern stacked. In production
accounts this shape hides among hundreds of grants, which is why
reviewers script these graph walks instead of scrolling, collecting
every invoke-allow alongside every pass-allow and asking where each
arrow lands. Notice too how the Deny statement earns its keep: direct
assumption would shortcut the whole design, so someone explicitly
nailed that door shut while leaving the window beside it open.

## Executing the chain

The mechanics reward careful HTTP more than cleverness. Invoke
nightly-report with pass_role set to report-runner; the response's
contextToken is your new operating identity, verifiable at /whoami
with the X-Sim-Context header. Wearing that token, invoke
admin-console with pass_role set to admin-role to receive a second
token. Only the final token satisfies /admin/context, presented as a
Bearer authorization or the same sim header. Each failed attempt
explains itself, naming whether invoke or pass was refused for whom,
so missteps teach rather than punish. Keep a small log of tokens as
you go, because context switches are cheap to confuse when two
similar strings sit in your scrollback; verifying at /whoami after
each hop costs nothing and prevents the common mistake of presenting
the first-hop token at the final door. When the page finally renders
with your flag, notice what unlocked it: no password, no exploit
code, just two legitimate capabilities composed in an order their
author never intended. That is the signature of cloud privilege
escalation, and spotting it on paper is the skill this room drills.

## Scope

Confine yourself to http://target:8000 within your own instance.
The console has no route anywhere else, holds no secrets beyond its
own flag, and resets completely on restart, so the chain you build
must be rebuilt honestly every time rather than remembered by the
server. Everything needed is published through documented endpoints;
there is nothing to brute force and no benefit to hammering the admin
endpoint, since it answers only to a token you must earn through the
chain. The ARNs and account number 111122223333 are invented
placeholders from the documentation examples of the world, not
anyone's real account. If an invoke returns AccessDenied, treat it as
information: the error names the identity, permission, and resource
involved, and that feedback loop against readable policy documents is
precisely the muscle cloud security reviewers build. Practice it here
where the stakes are printed flags, then carry it somewhere that
matters. When you finish, close the loop as a defender would: ask
which single grant you would remove to break the ladder, and notice
that the answer is rarely the dramatic admin policy and almost always
the small pass permission sitting quietly on a developer account.
