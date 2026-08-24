# Kubernetes Paper Walls

Kubernetes authorization is a graph drawn on paper: service accounts
hold tokens, roles list verbs, bindings connect the two. The walls it
builds are real until someone can read the paper, write new lines on
it, or both at once. This room compresses a full escalation chain,
the kind that ends with an exec shell inside production, into one
namespace you can walk in under an hour. The pattern it teaches shows
up in real clusters constantly, because service accounts are created
generously and their rights are reviewed rarely. An automation
account gets secret reads for one job and keeps them forever; another
gets binding rights during a migration and nobody remembers why.
Individually each grant has a plausible story, and the cluster hums
along without complaints until one account becomes the stepping stone
to the next. Auditors who understand this chain stop seeing RBAC as
a list of permissions and start seeing it as a directed graph where
the dangerous nodes are not the powerful ones but the ones that can
edit the graph itself.

## What is real here, and what is simulated

The apiserver on port 8000 is a Flask process serving dictionaries,
and its landing page says so plainly. There is no etcd, no kubelet,
no container runtime, and no node anywhere; the pod you eventually
enter is one JSON object and its exec endpoint returns canned output
wrapped around this session's flag. What behaves faithfully is the
authorization machinery. Bearer tokens map to service accounts the
way projected tokens do in real clusters. Permission checks recompute
from the live binding list on every request, so a binding you create
changes what your next request may do, exactly as the real RBAC
authorizer would decide it. Secrets arrive base64-encoded inside JSON
data fields because that is genuinely how the API encodes them, and
decoding a stolen token before using it as a bearer credential is the
same motion defenders teach and attackers repeat. Even the redacted
flagship token is honest about cluster habits: some secrets exist
that you will not get to read.

## Walking the graph like an auditor

Begin with selfsubjectrulesreviews, the sim's version of kubectl auth
can-i --list, because knowing your own rights prevents wasted
guessing. metrics-agent reads secrets and lists pods; that pairing
matters more than either half alone, since pods tell you which work
is worth attacking while secrets fund the attack. Next, read every
role binding and resolve each roleRef against the roles list. The
question to hold in mind is not who has power but who can change who
has power: any account bound to a role allowing create rolebindings
can redraw the authorization graph itself, which makes that account
the most valuable target in the namespace regardless of its own
permissions. deploy-bot holds exactly such a right here, and its
service account entry names a mounted-token secret. Service account
tokens live in secrets by design so their owning pods can mount them;
a reader-wide secret grant turns that design into a handoff of
identities.

## Escalating, then entering

Wear the decoded deploy-bot token and confirm the switch with
selfsubjectrulesreviews again; identity here is nothing more than
possession of a string, which is the uncomfortable truth about bearer
credentials everywhere. deploy-bot still cannot exec, but it can
create rolebindings, and the roles list contains prod-admin with
pods/exec create. POST a binding pointing that role at deploy-bot.
The apiserver recomputes permissions immediately, which you should
verify rather than trust: selfreview now shows the exec verb. This
verify step matters more than it looks, because real RBAC graphs
hide surprises such as conflicting bindings or an existing grant you
had not noticed, and confident escalation means reading back what the
authorizer now believes about you. List pods, pick flagship-0, and
POST an exec command of cat against /var/run/secrets/flag.txt. The
stdout carries FLAG{...}, this room's per-session value. Then read
the remediation column of your mental notes: scope secret reads to
specific names, treat binding-create rights as admin-equivalent,
and alert whenever a service account grants itself anything.

## Scope

All work happens against http://target:8000 inside your own lab
instance, which cannot reach the internet, other labs, the host, or
the control plane. Tokens in this room are fixed training strings
with no validity outside the container, and the binding you create
lives only in memory until restart erases it, so both passes of the
platform's solver rebuild the whole chain honestly. Use the
documented endpoints; there is nothing behind guessing paths,
flooding requests, or probing beyond the namespace, and every correct
move is visible in the graph the API publishes about itself. If a
request answers 403 Forbidden, read its message: it names the service
account and action involved, which is precisely the feedback real
clusters give auditors. Practice reading those refusals as signposts
instead of walls, here where they cost nothing. The habits worth
carrying out of this room are enumeration before action and
verification after every identity change; both translate directly to
kubectl-driven reviews of clusters that belong to employers who will
not be nearly as forgiving as a Flask process with a flag inside.
