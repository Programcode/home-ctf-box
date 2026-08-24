# Web Trail

Web server logs are the security camera footage of the internet: most of
what they record is boring on purpose, which is exactly why the
interesting frames survive unnoticed. Ten thousand requests is far too
many to read one by one, so investigators work the way a video analyst
works, scanning for shapes that do not belong and then zooming in. In
this room one night of storefront traffic from the Meridian Archive sits
in an Apache combined format access log. An intruder moved through it in
three acts: an automated sweep of the product pages looking for SQL
injection, a burst of password guesses against the login form, and then,
once something worked, a single administrative sign-in issued from fresh
infrastructure with a scripting library instead of a browser. Your job
is to name all three facts on the incident report.

## What is real here, and what is simulated

No real attack traffic touched anything while this evidence was made.
The log is assembled at import time inside a small Flask application
from fixed pools of addresses, paths, and user agents, so it comes out
byte for byte identical on every run and every learner sees the same
case. What is faithful is the shape of the story. Attack tools really do
announce themselves in User-Agent strings more often than beginners
expect, credential guessing really does show up as a wall of identical
requests answered with authentication failures, and the moment an
attacker succeeds really does look like one quiet line where the status
code changes from 401 to 302. The pivot to a second source address is
also true to life, because noisy tooling gets blocked or burned and the
operator continues from somewhere cleaner. Practicing these patterns on
synthetic bytes builds the same reflexes you would use on production
logs during an actual incident.

## Working the log like an investigator

Start with signatures before you start with theories. Grep the file for
known tool names and count what you find; the sweep in this log signs
itself on every request, and counting tells you whether you are looking
at a probe or a campaign. Next aggregate: cut the first field off every
matching line, sort, and count unique values, because one address
repeating hundreds of times is an attacker and ten addresses repeating
twice are probably customers. Then chase the authentication endpoint.
Every POST to /login in this log belongs to the attackers, so filter out
the failures and see what remains. A 302 response means the server
accepted credentials and redirected, which makes the survivor your best
evidence: read its query string for the compromised account and its last
quoted field for the agent that signed in. Notice the second address on
that line and ask yourself why the intruder changed infrastructure
between the noise and the success. File all three answers at the report
desk and the case closes.

## What you will practice

- Filtering large logs by tool signature and status code.
- Aggregating attacker sources with sort and uniq style pipelines.
- Reading one decisive log line for account and agent evidence.

## Scope

Only the case page at `http://target:8000` is in scope. Nothing
outside your lab instance is a target.
