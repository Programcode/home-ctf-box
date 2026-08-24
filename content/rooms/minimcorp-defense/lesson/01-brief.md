# minimcorp-defense

The best red teamers can flip to the other side of the wire without
changing gears, and that is exactly what this room asks of you. The
MinimCorp breach you may already know from the attacker's perspective
is over, and the estate owners have frozen every relevant log into four
exports before anything was touched. You inherit the case: one external
actor, three simulated hosts' worth of artifacts, and a night's worth
of activity compressed into a handful of events. Your job is not to
guess. Every answer the console will accept is derivable from the
evidence plus the playbook, which spells out precisely how each stage
is graded. That is deliberate. Real incident response is a discipline
of defensible claims, where an analyst who cannot say why a timestamp
is right or why an identity belongs in scope is adding noise to an
already loud room. Work slowly, read everything twice, and let the
exports argue your conclusions for you.

## Reading evidence like an analyst

Open /case for the brief, then /playbook before you touch any data.
The playbook is your grading contract: it defines the stage vocabulary
for the timeline, the exact rule for counting affected identities, and
the containment options with their effects spelled out. Only then fetch
all four exports from /evidence and read them end to end, including
rows that turn out to be noise. The edge access log gives you the
first stage almost for free, a config artifact fetched at a precise
minute by an external address. The wiki audit shows the same service
account authenticating minutes later from that same outside source,
which is the reuse moment. The finance export lists exactly which
invoice records left the building, with employee ids attached. The
directory-sim log closes the story with a token issued to a privileged
principal. Four files, one narrative, no gaps. Correlation across
sources is what makes each file stronger than it looks alone: an IP
address repeated across exports ties stages together, and a timestamp
from one system corroborates an event in another, which is exactly how
you should be reading every multi-source case that lands on your desk.

## Timelines that survive review

The timeline stage wants four steps in order, each mapped to its slug,
each stamped with the minute-precision time taken from the first event
of that stage. Precision matters here because it mirrors how timelines
are actually challenged in incident reviews: a respondent who claims
the logs are ambiguous, or a lawyer who asks when exactly access began,
will get an answer built from first events, not vibes. Notice also what
the exercise teaches about noise. The wiki audit contains a perfectly
innocent login from an internal address earlier that evening, and part
of reading evidence like a professional is deciding what belongs in
the attack narrative and what stays context. If your submission is
rejected, the console tells you which stages remain wrong rather than
which entries, so keep your own working notes as you go. Write down the
evidence line that justified every timestamp you submit, because in a
real war room the analyst who can point at the row wins the argument,
and the one who cannot re-opens the whole timeline for everyone.

## Scoping identities without guessing

The accounts stage applies a rule you should steal for real work: an
identity is affected when the attacker authenticated as it, when it was
impersonated, or when the estate handed that identity's restricted
records to the attacker. Apply that rule mechanically across all four
exports and a specific set falls out, including two employees whose
only involvement was having their records enumerated. Just as
important are the names that do not belong: colleagues mentioned in
logs, owners of untouched records, benign logins from before the
window. Overbroad scoping burns goodwill and triggers pointless
notifications; underbroad scoping leaves people exposed. The rule
exists because defensible scope beats instinctive scope, and the
console grades exactly the defensible set. Notice how the same export
can carry both an affected identity and a bystander a few lines apart,
and how only the written rule separates them reliably at two in the
morning under pressure, which is precisely when scoping decisions are
actually made in real response work.

## Containment is triage with constraints

Containment is where blue teams earn their salary, and where this room
is strictest. The playbook offers eight actions with plainly stated
effects; the grading rule requires that every root cause the chain
exposed gets covered, nothing destructive enters the plan, and nothing
healthy goes offline. Five actions satisfy all three constraints, and
each maps to a specific failing you watched happen in the timeline:
the stale edge backup, the reused service secret, the static finance
key, the legacy signing scheme, and the missing per-record check.
Rejecting the bad options is half the exercise, because power-cycling
the edge, deleting audit trails, or rotating a single password are all
real proposals that real teams make under pressure, and each fails a
named constraint rather than merely being unpopular. Practice saying
why an action is wrong: availability harm, evidence destruction, or
scope too narrow. Those three categories cover most containment
mistakes you will ever review, and being able to name them turns a
heated debate into a checklist. When all three stages read accepted,
close the case and collect the flag.

## What is simulated here

Say it plainly: this is one Linux container, disclosed identically on
the landing page, in the safety notes, and here. A single Flask app
serves synthetic exports shaped like real logs plus a small stateful
case API; there is no SIEM cluster, no shipper, and no corporate
network anywhere in the box, and state resets on restart. No real
malware, exploit code, or captured credentials exist in the image, and
nothing leaves the container. The logs describe invented people and
addresses chosen for documentation ranges, so nothing here points at a
real company or person. What transfers is the method: read the grading
contract before the data, correlate exports into one ordered narrative,
scope identities with explicit rules instead of sympathy, and choose
containment that fixes causes while preserving evidence and
availability. Those habits are the deliverable; the flag just proves
you did the work, and the same habits transfer unchanged to whatever
log sources and case systems your first real team hands you.
