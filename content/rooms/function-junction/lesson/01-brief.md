# Function Junction

Serverless platforms promise that functions are small, scoped, and
boring. Then someone wires an HTTP trigger without authentication
because a partner integration was urgent, and someone else leaves a
debug switch in the handler because it helped during on-call. Each
decision is defensible alone. Together they mean any stranger on the
internet can run your function and steer where its output goes while
it helpfully attaches its own secrets to the parcel. Incident case
studies involving serverless keep returning to this trio: an open
trigger, a verbose mode nobody remembered enabling, and a handler
that trusts its caller more than it should. The economics favor the
attacker too. Functions scale automatically, so a single unauthenticated
invoke endpoint is not one door but as many doors as the attacker has
requests for, and the platform bills the victim for the privilege.
This room shrinks that scenario until you can hold all of it in your
head at once and watch each piece contribute to the leak.

## What is real here, and what is simulated

The junction console is a Flask process wearing a serverless costume,
and the costume says so on its front page. There is no provider, no
region, and no billing surprise; the two functions are dictionaries
describing triggers, runtime, and behavior, and the invoke endpoint
interprets those dictionaries with plain Python. One seam deserves
honest attention: a real exfiltration needs somewhere to send data,
but your lab network cannot route to the internet, so the appliance
hosts /sink as a stand-in for the webhook collector you would run on
your own infrastructure. Pointing destination_url at it is exactly as
meaningful as pointing at an attacker-controlled host, minus the
felony. The environment summary the debug mode leaks is fabricated
training data arranged around this session's flag, which mirrors how
production handlers really do carry credentials, tokens, and signing
keys in their process environment. Database URLs, API keys, and
signing material all live one os.environ lookup away from whatever
code runs in that process, which is precisely why debug output that
dumps the environment counts as a secret disclosure and not as a
logging convenience.

## Finding the weak function

Start by reading the platform the way an auditor would. GET /functions
returns both handlers with their trigger configuration attached.
thumbnailer declares a storage event source with signed auth; invoking
it by hand returns a polite refusal. webhook-relay declares http-event
with auth none, and that single field is the entire vulnerability
brief: no signature means no caller identity, which means every
capability the handler exposes belongs to everyone. The function's
detail page then hands you the second half voluntarily. Its
debug_mode block documents how to activate diagnostics and what they
contain. Real incidents look like this from the outside: nothing
hidden, no exploit needed, just configuration pages describing a
disaster in polite JSON. When you find documentation admitting a
debug mode exists, read what it leaks before you assume it is inert,
and check who can trigger it, because a debug switch behind signed
auth is a risk while the same switch behind no auth is an incident
waiting for a date.

## Steering the delivery

The relay takes a destination_url from whoever invokes it, which
converts the function into your courier. Compose an invoke whose body
sets that URL to your collector, include any small payload so the
delivery looks like ordinary traffic, and set debug_hook true. The
handler builds the outbound body with your payload plus diagnostics,
performs the POST, and reports delivered. Your collector now holds
the full envelope, and events[0].diagnostics.environment carries the
SECRETS_BLOB value verbatim: SMTP passwords, metric tokens, a Slack
hook, and one backup signing key slot containing FLAG{...}, which is
this room's per-session submission. Notice the shape of what just
happened. You never touched the secret store; you asked the platform
to hand its own environment to an address of your choosing, which is
why egress controls and payload validation belong next to every
serverless trigger. In a production account the same request pattern
against a real relay would land credentials in an attacker's inbox
within seconds of finding the open trigger, and the platform's own
logs would show nothing more alarming than successful invocations.

## Scope

Stay inside http://target:8000 on your own instance. The appliance
cannot reach the internet or anything else, /sink exists solely
inside it, and every secret in SECRETS_BLOB besides the flag is
invented filler. The intended path uses only documented endpoints;
there is no need to guess routes, flood the invoke endpoint, or test
SSRF against internal addresses, since the console already tells you
where deliveries may go. If thumbnailer refuses your invocations,
that refusal is correct behavior worth appreciating rather than
defeating, and nothing behind it belongs to this room. The lesson to
keep is about composition rather than any single flaw: unsigned
triggers plus debug switches plus caller-chosen destinations compose
into exfiltration, and each half of the pair is visible in plain
configuration long before anyone exploits it. Audit your own
platforms for exactly this trio, ask what a debug flag would disclose
if a stranger could flip it, and assume that any endpoint accepting
a destination URL will eventually receive one you did not approve.
