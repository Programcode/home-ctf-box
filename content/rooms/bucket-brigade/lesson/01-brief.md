# Bucket Brigade

Object storage is where discipline goes to relax. Buckets accumulate
backups, exports, and one-off files, and every one of them carries a
policy document deciding who may list and who may read. The failure
mode this room teaches is quiet: a single statement with a wildcard
principal, added during a migration, never reviewed, sitting in front
of the most boring bucket in the account, the nightly backups. Nobody
notices because nothing breaks. Data simply leaves whenever someone
guesses the URL, and attackers guess URLs professionally. Researchers
who scan address ranges for open buckets publish their totals
regularly, and the numbers stay embarrassing year after year, not
because storage services are hard to configure but because nobody
re-reads policies after the migration sprint ends. This room gives
you one such bucket, small enough to enumerate completely, so you can
feel how little effort complete exposure takes from the outside.

## What is real here, and what is simulated

The appliance on port 8000 is a small Flask application pretending to
be an object storage service, and it says so on its landing page.
There are no credentials because there is no cloud; buckets, objects,
and policies are dictionaries built deterministically at startup, so
the same listing appears after every restart. What mirrors reality is
the shape of the interaction. Listings really do paginate with a
marker and a page size, object reads really are separate requests
from listing, policy documents really are JSON statements of effect,
principal, action, and resource, and anonymous access really is the
default posture when no authentication headers are sent. Two of the
three buckets reject anonymous callers outright, which is your
control group for what correct looks like. When the third answers
happily with no identity at all, you have found the misconfiguration
without touching anything but GET requests.

## Why pagination matters more than it looks

It is tempting to fetch one page of a listing, see database dumps,
and move on. That instinct is exactly what this room punishes. The
first page of nimbus-nightly-backups holds only db and logs keys;
the sensitive file sits deep enough that skipping pages means missing
it. Real listings behave the same way at any meaningful scale, which
is why auditors script their enumeration instead of eyeballing it:
request a page, record next_marker, request again, stop when
is_truncated turns false, and reconcile the collected keys against
the reported total count. A loop of four or five requests covers this
bucket; at production sizes the same loop covers millions of objects,
and it is the only method that can truthfully claim completeness.
Notice also how much the key names tell you before any download.
Nightly archives, manifests, sync logs, one postgres snapshot, and
then an ops path mentioning an incident and a keyring. In real
exposures, the filename is frequently the entire breach notification,
because people name files by their worst contents.

## Turning exposure into evidence

Once the listing surfaces ops/incident-2026-07/keyring-recovery.txt,
fetching it is one GET, since the same wildcard principal covers
GetObject as well as ListBucket. Read what comes back: recovery notes
for the July incident ending in a recovery flag, which is this
platform's per-session value and the thing you submit. Then do the
defender half in your head. A finding like this closes with three
moves: remove the wildcard statement, rotate whatever was exposed on
the assumption adversaries already saw it, and enable logging or
audit alerts so the next anonymous listing shows up somewhere other
than an attacker's terminal. Rotation deserves emphasis, because the
common mistake is fixing the policy while treating the exposed data
as safe again; anyone who listed that keyring file months ago still
holds what it contained. The uncomfortable truth about public buckets
is that you rarely learn of exposure from your own telemetry; you
learn it from researchers, scanners, or worse, which is why periodic
policy review exists as a chore worth doing rather than a box to
tick.

## Scope

Only http://target:8000 inside your own lab instance is in scope.
The sim has no route to the internet, other labs, the host, or the
control plane, and every object in it is fabricated training data.
Enumeration here means walking the documented pagination parameters
of one endpoint you have been handed; there is no need to scan,
brute force keys outside the listing, or hammer the service, since
the intended discovery is fully visible through honest use of the
API. Treat the 403 buckets as confirmation of good hygiene rather
than obstacles to defeat. Nothing in them is part of this room, and
no technique taught here involves defeating an AccessDenied response.
If you feel the urge to guess secret key names, redirect that energy
into finishing the marker walk properly, because thoroughness is the
actual skill being graded. The same restraint applies to request
rate: a patient loop with ordinary spacing completes the walk in
seconds, and learning to enumerate politely is what separates an
auditor from a liability when you eventually run these habits against
infrastructure that belongs to someone else.
