# purple-replay

Detection engineering is the craft of being loud about attacks and
silent about everything else, and the only way to learn it is to feel
both failures personally: the rule that misses the attack, and the rule
that pages you at three in the morning because someone typed a
password wrong twice. This room makes you live on both sides of that
line. You get a complete attack script, four stages of a tidy little
intrusion, and you run it exactly as written against a victim
application. Then, before you are allowed to advance, you must write
the detection that would have caught it, and the lab grades your rule
immediately against everything it knows: the attacker events you just
generated plus a fixed pool of ordinary traffic full of near misses.
Four gates, four rules, one final re-check of them all together. The
pacing is deliberate, because you cannot sprint to the flag by running
the whole script first and writing rules afterward; each gate only
opens once its stage's rule has been validated against traffic that
exists at that moment. That restriction mirrors real purple work,
where detections are agreed and tested while the replay is fresh
rather than reconstructed weeks later from memory and stale captures.

## Reading the script before running it

Start with /lab/stages rather than the raw shell script, because the
stage document tells you what each stage means, what signal it leaves,
and the exact structured steps you are about to execute. The replay
discipline matters more than it first appears. Every request carries an
X-Src-Ip header representing what the border router would have stamped,
and the whole exercise depends on you setting it honestly for attacker
traffic instead of letting requests blend into internal addresses.
When professionals replay adversary tradecraft from a report or a
threat intel feed, faithfulness is the entire point; a sloppy replay
generates events no real intrusion would have produced, and detections
tuned on sloppy replays fail precisely when they matter. Run stage one,
two requests for development artifacts and server status, and watch
how unremarkable each request looks on its own. Nothing about either
request is malicious in isolation; what makes them signal is the artifact
being requested, which is exactly the attribute your first rule should
key on rather than any imagined aura of wrongdoing.

## Thresholds versus lone events

Stage two is where the room teaches its most transferable lesson. Seven
failed logins in a burst is an attack pattern; two failed logins from
genuine users who forgot their passwords is Tuesday. Your brute-force
rule has to separate those worlds using only event fields, which pushes
you toward two ideas at once: match on the combination of path and
status code, then demand a minimum count before firing. Set the
threshold too low and the gate shows you exactly how many benign
events your rule would have flagged; set it absurdly high and the
attack itself stops clearing it. The gate's feedback gives you hit
counts either way, so tuning becomes a conversation with data instead
of a guess. That loop, draft rule, see counts, adjust, is the actual
daily work of detection engineers, compressed here into seconds. Keep
the two-condition shape in mind as well, because path plus status is
where most login detections live in production too, and single-field
rules on shared endpoints are the classic source of noisy alerts that
teams eventually mute instead of fix.

## Content patterns and volume signals

Stages three and four round out the two other families of signals you
will tune forever. The traversal exploit is a content pattern: the
attacker cannot help but send ../ sequences if they want the technique
to work, so a rule keyed on that substring catches every variant while
benign downloads name plain files and never trip it. The exfil stage
is a volume signal: nothing about one upload request looks special
except its size, and size turns out to be enough because legitimate
uploads sit orders of magnitude below the stolen bundle. Notice the
shape of your final rule set: one pattern rule, one threshold rule,
one content rule, one volume rule. Almost every production detection
you will ever write or review is some composition of those same four
ideas, and this room made you derive each one from evidence you
personally generated. That provenance matters: a rule you can justify
row by row survives review, while one copied from an internet gist
gets quietly disabled the first time it pages someone for nothing.

## What is simulated here

Say it plainly: this is one Linux container, disclosed identically on
the landing page, in the safety notes, and here. The same Flask process
plays victim and lab, the benign pool is a fixed list loaded at boot,
and every restart wipes events, gates, and stored rules so each pass is
identical. No exploit payloads exist in the image; the traversal merely
returns simulated file text, the brute force checks a prefix, and the
exfil bundle is a number in a JSON body. Nothing executes beyond the
process and nothing leaves the container. The attacker address belongs
to a documentation range and the benign users are invented, so nothing
here points at real infrastructure or people. What transfers is the working
rhythm of purple teaming: replay faithfully, attribute honestly, write
the detection while the attack is fresh, let immediate validation
punish noisy rules, and never trust a rule you have not re-checked
against normal traffic. The flag arrives only when all four habits do.
