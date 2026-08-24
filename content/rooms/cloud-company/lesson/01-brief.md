# cloud-company

Cloud incidents rarely announce themselves; they compound. A role that
can become another role, a bucket that answers one anonymous request too
many, a function revision nobody read, and an audit log that somebody
tried to tidy are each minor findings on their own. Strung together
they are a full compromise, and that stringing is what this room
teaches. You start as the most boring principal imaginable: a developer
onboarding key printed in public documentation, the kind of credential
every real estate has in abundance. From there, five stages walk you up
the IAM graph, into private storage, through someone else's backdoor,
and finally into forensic accounting for deleted history. Each stage
pays one fragment of the master flag and each fragment is earned by
demonstrably completing the stage, not by pattern matching the last
room. Take the stages in order even where a shortcut seems to exist,
because the estate deliberately chains its dependencies: later stages
demand artifacts, tokens, or answers that only earlier stages produce,
and skipping ahead leaves you holding fragments you cannot justify.
That is by design, since real cloud compromises are also cumulative,
each small grant quietly funding the next request until nobody can say
exactly when access became ownership.

## Escalating by reading

The IAM service hands its full graph to any authenticated caller:
users, roles, and every policy statement including the two nobody ever
reviewed. Resist the urge to brute force. Read the statements like a
map: dev-onboard may assume ci-runner, ci-runner may assume deploy-bot,
and deploy-bot carries a break-glass assume straight onto ops-admin
that was added in 2024 and forgotten. Three POSTs later you hold the
keys to the estate, and the console summary rewards you with both the
first fragment and two leads worth following. The lesson generalizes:
privilege escalation graphs are documented by their victims. Policies
are written down, stored, and readable by exactly the principals they
govern, so enumeration is not an attack technique, it is due diligence.
What separates attackers from auditors is what they do with the map.
When you finish, ask how many edges your own organization's graph has
that nobody has read since the quarter they were added, because
unreviewed trust between automation identities is where estates quietly
grow admin paths nobody remembers approving.

## Public reads rarely stop at public data

The s3 service lists two buckets, and cc-public-assets answers anonymous
requests because vendor integrations need it. Among the site assets sits
a vendor manifest whose text casually names a confidential mirror:
cc-finance-archive holds a q1 ledger extract, copied there quarterly by
ops because granting vendor accounts was politically harder than
widening a policy. Fetching the extract requires your fresh ops-admin
token, which is the point: the anonymous listing is the pivot, the
privileged identity from stage one is the key, and neither alone leaks
anything. When you hold the ledger and the second fragment, notice how
mundane every link was. Real cloud exposures look like this, boring
configuration decisions that only become incidents in combination. The
manifest even documents its own bad reason for existing, a workaround
nobody revisited because the workaround kept working, which is how most
dangerous storage policies are born: not from malice but from a ticket
closed quickly three years ago.

## Finding the door someone else installed

Stage three turns you from intruder into inspector. The functions
registry lists three functions; image-resizer has three revisions, and
revision 7 was authored by maintenance-ci, an automation identity, with
a note about a cache warm pinger. The code view shows what the note
means: every invocation posts metadata to an external callback address,
and the revision added a daily trigger besides. Your verdict POST
confirms revision 7 and pays the third fragment. This stage teaches the
review habit that matters most in serverless estates: deploy histories
are attack surface, identities without human owners deserve suspicion,
and reading code that already runs in production is cheaper than
responding to what it does. Ask who approved maintenance-ci and the
honest answer is nobody remembers, which is precisely the gap a
backdoor needs. Scheduled triggers deserve special suspicion because
they guarantee repeated execution even when nobody invokes the function,
turning one quiet revision into a persistent channel that looks like
routine workload in every per-invocation metric you already collect.

## Auditing deletion itself

The final stages make you prove what happened using mathematics rather
than trust. Audit entries are hash chained: each record's hash covers
its predecessor's hash, actor, and action, so recomputing the chain
from genesis exposes any splice. Entry 42 is where stored reality
diverges from recomputation, proving records were deleted after 41. The
quarantine holds what the deleter thought was gone: three soft-deleted
records naming maint-bot, including one copying the very ledger you
read earlier to an external endpoint. Two verdict POSTs, one for the
deletion set and one for the destination, pay fragments four and five.
Assemble all five at /board and the controller returns the master flag.
Notice what made the cover-up fail: deletion without quarantine purge,
and a chain whose hashes bind each record to its neighbor. Attackers
who edit history usually assume logs are prose they can rewrite; treat
every log you depend on as a claim to verify mechanically, because the
difference between an allegation and a finding is whether you can show
the arithmetic.

## What is simulated here

Say it plainly: this is one Linux container, disclosed identically on
the landing page, in the safety notes, and here. Four Flask apps bind
to four loopback ports inside the box, a controller routes by Host
header the way an internal mesh routes by service name, tokens are
strings derived from this session's flag, buckets are dictionaries, and
the hash chain is sha256 over plain text. No cloud account exists,
nothing executes beyond the process, nothing leaves the container, and
every restart rebuilds identical state. The callback address is a
documentation-domain placeholder that resolves nowhere. What transfers
is the method: enumerate policies before touching credentials, treat
anonymous reads as reconnaissance surface, read deploy histories of
things that already run, and never trust a log whose chain you have not
personally recomputed. Those four habits survive far beyond this box,
and they compose: an auditor who reads graphs, listings, deploy logs,
and chains in that order will find the compound story that single-issue
scanners always miss.
