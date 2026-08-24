# blue-screenplay

When something bad happens on Windows, the first two questions are
always the same: what does the event log say, and which channel holds
it. Security records authentication: logons that succeeded, logons
that failed, tickets requested and granted or refused. System records
the machine's own health: services starting, stopping, and crashing.
Read those two channels together and an intrusion stops being a
mystery and becomes a timeline with named actors, timestamps, and a
direction of travel. This room hands you exactly those exports from a
simulated three-host estate that was hit overnight, plus an asset
inventory mapping hostnames to addresses, and asks you to turn all of
it into three concrete findings an incident lead could act on.

## Reading the channels like an analyst

Security channel work starts with failures, not successes. A single
failed logon means someone mistyped a password. Seven failures in four
minutes against one account from one outside address is an answer:
someone is guessing credentials, and the next success from that same
pair tells you exactly when they stopped needing to guess. Pay
attention to the shape of each record too: source address, target
account, destination host, timestamp, logon type. Those five fields
carry almost every authentication story you will ever tell, which is
why analysts internalize them before learning any fancy tooling. The
System channel then adds the plot. Services dying in sequence during
the intrusion window, ordered by time, mark where the intruder stopped
walking around quietly and started breaking things, and the first
casualty often tells you what they feared most, because security tooling
is usually killed before it can raise the alarm. Read both channels
once end to end before forming any theory at all, then reread with
one.

## Correlation beats collection

The individual events in this pack are unimpressive on their own. The
story lives between them. After the initial success, watch what the
compromised account does next: which hosts it appears on, and crucially,
which internal address sits in the source field of those new logons.
When one machine starts authenticating as an account it should not
hold onto other machines it has no business touching, that is lateral
movement, and the source address names the first victim host with
certainty. Business-hours logons from the admin jump host will try to
distract you; accounts, times, and direction separate noise from
signal every time. Build the habit now of writing the timeline down as
you go, one row per finding, because in real incidents you will be
reassembling this story days later for people who were not there, and
memory alone loses rows. A timeline you can hand to someone else is
worth three timelines that live in your head.

## Filing your findings

Incident reports earn trust by being precise, so this room grades the
way a good incident lead reads. Not "some backup account," but the
exact account name. Not "a service crashed at some point," but which
service died first and how the System channel proves it. Not "they
moved sideways somehow," but the specific internal source address
behind every post-compromise hop. The report endpoint checks each of
your three answers independently and returns true or false per field,
partial credit does not exist, and a complete match verifies your
report and returns the flag. Derive all three answers from the exports
before you submit anything. If a field comes back false, reread the
channel rather than guessing again; the logs contain every answer, and
the difference between analysts who improve and analysts who plateau
is whether they treat a wrong answer as a reason to look harder or an
invitation to gamble.

## What is simulated here

Plain disclosure: this box is one Linux container running a small web
application. No Windows kernel exists, no event pipeline runs, and the
evtx-sim files are static JSON regenerated identically on every boot,
with event IDs suffixed -sim so nobody mistakes them for genuine
Microsoft telemetry. The container holds no malware and executes
nothing hostile; it is a filing cabinet with a grading script attached.
What transfers to real work is the method, and none of it depends on
file formats: channel selection, failure clustering, timeline
ordering, cross-host correlation, and precise reporting are identical
whether rows arrive as JSON over HTTP or from a real EVTX parser
inside a SIEM. Learn the questions here; the tools for answering them
at scale come later, and they will make far more sense once the
questions feel obvious rather than arbitrary. The evidence regenerates
identically on every boot, so rerunning your analysis against a fresh
container is always a fair test of your method.
