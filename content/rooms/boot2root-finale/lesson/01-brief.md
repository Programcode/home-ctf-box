# Boot2Root Finale

The boot2root tradition in vulnerable-machine training is a simple
promise: one machine, no hand-holding, and root as the finish line.
Images built in that spirit, from early community VMs to modern
container labs, keep returning to the same small set of obstacles
arranged in different orders. This finale arranges three of the
classics into one arc: services that hide until you knock politely,
credentials that leak through a share that should never have held
them, and a sudo configuration whose convenience becomes the last
step to root. If you can walk this arc unaided, you have internalized
the core rhythm of the genre.

## What you will practice

The opening move is patience against silence. Most of this box looks
closed: 8080 refuses connections outright because nothing is bound
there yet. TCP knocking works differently from the payload-based
variants: you prove knowledge of a sequence by completing plain
connections to three high ports in order within twelve seconds. The
exercise trains timing discipline and state tracking across separate
socket calls, and it demonstrates why production knock daemons pair
with short windows: a sequence spread too thin in time is worthless.

The middle section is source criticism applied to shared files. Once
the share browser appears, the incoming share greets you without any
authentication at all, which is exactly how such shares end up
holding things they should never hold. A weekly sync note lists
staff devices and, buried mid-line, working console credentials for
the sysop account. Reading the surrounding cleanup tickets tells you
the team already knows this class of mistake happens; finding the
credential anyway is the point. You will pivot those credentials
into SSH access, which converts a web-page leak into an interactive
foothold.

The final act is a privilege escalation that lives entirely in
configuration review. sudo -l reports a NOPASSWD grant for one
maintenance menu script, plus two defaults that matter: secure_path
is disabled and PATH is kept from your environment. Reading the menu
script shows it calls status-report by bare name, so whatever
resolves first in your PATH runs as root. You will write a two-line
shell shim, put its directory ahead in PATH, and let sudo execute it.
This pattern has ended countless real-world audits for one reason:
convenience settings accumulate silently until someone reads them
end to end, exactly as you just did.

## Scope

Only your own instance is in scope: SSH on 22, the share server that
appears on 8080 after a valid knock, and the three knock ports 4010,
5011, 6012. The escalation shim you write executes inside this
disposable container only, and its intended action is reading the
flag file; nothing persists, nothing reaches beyond the lab network,
and every credential involved exists solely in your session. The
knock state resets whenever the container restarts, so both the share
server's appearance and the root flag are repeatable proof rather
than one-time luck.

Root in this box is the end of the story, not a step toward anything
real, and the safety notes say so without hedging. What transfers to
real work is not the shim itself but the review discipline behind it:
enumerating groups before trusting accounts, reading share contents
with the assumption that anything anonymous will eventually leak,
and treating every sudoers default as attack surface until proven
otherwise. When you finish, write down each stage transition while it
is fresh: which knock opened which door, where exactly the credential
sat, and which two configuration lines turned a maintenance script
into root. That writeup habit is what separates learners who solved
a box from operators who can defend one.
