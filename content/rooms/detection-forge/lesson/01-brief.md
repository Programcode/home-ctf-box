# Detection Forge

Detection engineering is where security stops being about finding one
bug and becomes about finding every instance of a behavior, forever,
without drowning in noise. A good rule is a promise: everything this
pattern touches deserves attention, and nothing else gets flagged. The
craft lives in that double constraint. A rule that only matches the
sample you saw is brittle; an attacker changes one character and walks
through. A rule that matches too broadly burns analyst hours on false
positives until someone mutes it entirely. Professional detection work
is therefore test-driven: you write rules against labeled fixtures,
positive samples that must fire and negative lookalikes that must stay
silent, and you keep those fixtures forever as regression tests.

The four slots in this forge each teach a distinct precision problem.
Union-based SQL injection looks easy until you meet reunion selection,
where both keywords appear inside ordinary words; word boundaries and
flexible whitespace handling are the difference between signal and
embarrassment. Path traversal rules have to survive encoding tricks
like %2e%2e%2f while not firing on a filename with two dots in it or a
single harmless hop that normalizes away. Exfiltration through base64
query parameters collides head-on with legitimate long tokens like JWT
session params, so the rule has to pin parameter names rather than just
blob shape. DNS tunneling hides payloads in subdomain labels, and label
length is nearly unique to tunnels among real-world hostnames.

Working the room, you will read the labeled bundle, draft patterns in a
scratch buffer, submit the full set, and iterate against the validator's
per-rule feedback showing missed positives and false positives. That
feedback loop, not any single pattern, is the actual job skill: real
teams ship detections exactly this way against curated fixtures.

## Simulation disclosure

Every trace in the bundle is a short synthetic string defined inside
the room target. Nothing executes your patterns beyond Python's re
module over fixed lists, no live traffic exists, and no sample contains
working exploit code. Pattern length caps at 400 characters to bound
evaluation.

## What you will practice

- Writing regex detections that satisfy both catch-rate and precision constraints.
- Reading adversarial negatives to understand where naive patterns break.
- Iterating a ruleset through validator feedback until every fixture passes.

## Scope

Only the forge at `http://target:8000` is in scope. Nothing outside
your lab instance is a target.
