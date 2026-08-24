# Pipeline Spill

CI systems love to talk. Every step of a build echoes what it is doing,
and secrets regularly ride along inside those echoes. Most platforms
answer with masking: a filter scans each log line, finds anything that
looks like a credential, and replaces part of it with asterisks before
the line reaches storage. Masking works well enough that teams stop
worrying, and that comfort is exactly what this room takes apart.

The billing-api runner in this case uses two maskers at once. The deploy
step exports its token base64 encoded, and the log keeps only the first
twenty characters of the encoded form. A later verify step fingerprints
the raw token, and the log keeps the last four characters of that form.
Each line on its own looks harmless. The export line hides half an
encoded blob; the fingerprint line hides almost everything. Together
they are a puzzle with one solution, because base64 decodes in fixed
blocks and a clean twenty character prefix decodes to exactly fifteen
raw characters with nothing lost in the middle.

This is not a rare slip. Real incident reports describe tokens rebuilt
from a debug print plus an error message, or a truncated signature plus
a checksum line. The defensive lesson has two parts. First, treat any
log occurrence of a secret, masked or not, as grounds for rotation,
because you cannot prove the masks overlap completely. Second, prefer
secrets that never appear in logs at all: pull them from a vault at
deploy time, reference them by handle, and let the pipeline pass around
identifiers instead of values.

In the room you will download the leaked build output, read the mask
policy line to learn how much of each form survived, decode the
truncated base64 prefix, splice on the fingerprint suffix, and replay
the result against the deploy endpoint. The endpoint accepts only the
true token, so a correct reconstruction proves the leak end to end.

## Simulation disclosure

Nothing here touches a real CI system. The build log is static text
served by the room's own Flask app, the token is a constant defined in
the target source, and the deploy endpoint compares strings in memory.
No external service is contacted and no real credential exists anywhere
in the bundle.

## What you will practice

- Reading a mask policy and reasoning about which parts of a secret survive.
- Decoding partial base64 safely by respecting block boundaries.
- Reconstructing a credential from complementary leaks and proving it works.

## Scope

Only the case page at `http://target:8000` is in scope. Nothing outside
your lab instance is a target.
