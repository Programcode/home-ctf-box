# Alert One

Every security operations center lives or dies by its queue. Sensors,
mail gateways, and endpoint agents generate far more detections than any
human could chase, so the first skill a tier-one analyst needs is not
hunting and not malware reverse engineering, it is deciding, quickly and
defensibly, which alerts deserve attention and which ones are noise. In
this room you sit at the Meridian Archive training desk with eight
detections from a single night. Each one carries the fields a real queue
shows: a title written by whoever tuned the rule, a severity, the source
address, the account involved, a threat intel verdict on the indicator,
and any change ticket that might explain the activity. Your job is to
walk all eight and classify each as a true positive or a false positive
using the desk playbook, then submit your verdicts one alert at a time.

## What is real here, and what is simulated

Nothing in this lab talks to a SIEM, an EDR console, or a threat feed.
The queue is a fixed list served by a small Flask application inside your
lab container, the alerts describe events that never happened on real
networks, and every IP address and ticket number is invented. What is
faithful is the decision procedure. Real analysts really do triage from
enrichment fields rather than alert titles, because titles are written
to be noticed and enrichment is written to be checked. Threat intel
enrichment really is the fastest way to confirm that an indicator has
been seen before in malicious contexts, and change tickets really are
the most common reason a frightening-looking detection turns out to be
approved work. The two-question rule you practice here compresses those
habits into something checkable: confirm the indicator with intel, then
look for an approved change that explains it. Only when both questions
resolve the right way do you have a true positive.

## Reading an alert like an analyst

Start from the fields, never the title. A title such as "data staging to
external storage" sounds critical, but the row beneath it may show an
approved migration ticket covering exactly that volume to exactly that
tenant, which makes it explained activity. Work each alert through two
questions in order. First, did threat intel confirm the indicator? The
intel_hit field answers this directly. Second, is there an approved
change ticket attached? The change_ticket field answers this. The desk
playbook says an alert is a true positive only when the answer to the
first question is yes and the second is no. An intel hit with a covering
ticket is approved work, and no intel hit means nothing but the detector
stands behind the alarm. Notice what this rule trains: skepticism toward
severity, respect for context, and the habit of writing down why you
closed something, because the classify desk records every verdict you
submit and closes the queue only when the full set matches ground truth.

## What you will practice

- Triage eight alerts using enrichment fields instead of titles.
- Applying the two-question playbook consistently across a queue.
- Submitting verdicts through POST /classify until the queue closes.

## Scope

Only the training desk at `http://target:8000` is in scope. Nothing
outside your lab instance is a target.
