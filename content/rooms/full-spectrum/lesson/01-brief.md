# full-spectrum

The finale exists to answer one question about your time in this track:
can you hold an entire engagement in your head at once, attack and
defense, without dropping either? Earlier capstones compressed a chain
into fragments you collected host by host. This one goes further in
both directions. The red side is a complete kill chain across four
hosts with a server-side state machine that refuses to let you skip:
initial access through credentials the portal itself publishes for
exposure checks, a pivot that rides single sign-on into internal git,
privilege escalation by impersonating a live admin session on the core
database, and exfiltration staged out of the archive. The blue side is
the professional deliverable every real engagement owes its client: an
incident report graded line by line by a review desk that only opens
once the technical annex is complete. Both flags are required. That is
the whole philosophy of this room in one sentence.

## Running the kill chain clean

Start on the portal and read what it tells you. The security notice
about a partner breach is not flavor text; the defanged corpus it links
is exactly where credential-stuffing material comes from in real life,
and one of those reused pairs still works here. Test pairs against the
login endpoint rather than assuming, collect your session token, and
then notice how the pivot works: the intranet jump service and the git
service honor the same session header, so your DMZ foothold speaks
fluently to internal infrastructure. On git, read the CI pipeline
configuration like an attacker would and find the console key printed
in plain text because vault integration keeps slipping a quarter. The
core-db console accepts that key, lists active sessions including one
belonging to a privileged orchestrator account, and lets you impersonate
it. The archive then stages your dataset once you present the admin sid.
Four hosts, four stages, one state machine keeping you honest.

## Writing the report as rigorously as the chain

The ir service opens only after exfiltration succeeds, which mirrors
how reporting actually works: you cannot scope an incident before you
have finished understanding it. The rubric grades three things. Scope
must list every touched host in attack order, because a report that
misses the internal git hop understates blast radius to everyone who
reads it. Findings pair fixed slugs with severities you must defend:
credential reuse that granted access sits at high, direct-control
exposures like the pipeline key and admin takeover are critical, and
the unmonitored staging path is medium because it is a detection gap
rather than an entry point. Remediation ordering carries the risk
argument: rotate and vault the live key first since it ends active
access today, scrub the repository second, bind sessions third, alert
on staging volume fourth. The desk names each failed line, so treat a
rejection as free peer review from a demanding principal.

## What is simulated here

Say it plainly: this is one Linux container, disclosed identically on
the landing page, in the safety notes, and here. Five Flask apps bind
to five loopback ports inside the box, a controller routes by Host
header the way edge and internal load balancers would, the breach
corpus is synthetic, no database or archive exists beyond dictionaries,
and nothing leaves the container. Flags arrive per task as environment
variables, tokens derive deterministically from them, and every restart
resets all state so both passes are identical. No exploit code or
malware ships anywhere in the image, the addresses come from
documentation ranges, and every person named is invented. What
transfers is the discipline:
run a chain without breaking state, then write the document that proves
you understood what you did, scoped precisely, severity argued, and
remediation ordered by risk. Do both halves well and the finale pays
out twice, and the habits pay out for the rest of your career: every
subsequent engagement you run will end with a report, and the reviewers
on the other side will grade it exactly this way.
