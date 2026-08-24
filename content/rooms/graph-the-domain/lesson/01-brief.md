# graph-the-domain

BloodHound changed directory attacks by changing their shape. Flat
lists of users and permissions became a graph, and questions like "how
does this helpdesk account reach domain admin" became shortest-path
searches that a laptop answers in seconds. Attack paths nobody planned
started falling out of the data: reset rights chained through service
accounts, sessions on admin workstations, group memberships inherited
from years-old projects. This room teaches that shift honestly. The
collector data is fictional and served as JSON by a locked Flask app,
so nothing touches any real directory, while the reasoning you practice,
reading nodes, walking edges, computing distances, transfers unchanged
to real assessment tooling you will meet later on this track. The room
also plants the defender's habit early: every attack path you find here
is an edge someone could remove, and noticing that duality is half the
value of learning graph analysis at all. Five questions stand between
you and the flag, and every answer lives inside the JSON.

## What is real here, and what is simulated

The platform runs Linux containers only, and this room never fakes more
than it needs. What you get is one Flask application serving a
collector-style JSON document at /collect/graph.json with twelve nodes
and twelve edges whose relationship names mirror real attack-path
tooling: MemberOf joins users to groups, CanResetPassword lets one user
set another's password, HasSession places a user interactively on a
machine, and AdminOn grants a group local administrator rights over a
host. The people, machines, and groups are invented; no LDAP query,
Kerberos ticket, or directory connection exists anywhere in the
container, and the response headers carry a simulation notice beside
the page banners. The quiz at /quiz checks your five answers
server-side against the exact expected set using case-normalized
comparison and prints the per-session flag only when every answer
matches, so partial knowledge earns nothing and guessing cannot
converge. Hop counting is pinned down precisely on the method notes:
edges traverse in both directions and one edge equals one hop, which
keeps every question deterministic across restarts. The reasoning is
real; only the directory is pretend.

## Why graph thinking wins

Flat enumeration answers what exists; graphs answer what it takes to
get somewhere. A password-reset permission looks minor in an ACL dump
until the graph shows it two hops away from a domain admin's account,
and a boring file server becomes interesting the moment an operator
group admins it while a service account holding reset rights logs into
it interactively. That exact chain sits buried in this room's data, and
once you have walked it manually you will recognize the shape
everywhere: collectors ingest sessions, memberships, and control
rights, then shortest-path queries surface routes no single list
reveals. Defenders run identical queries against identical data, which
is why edge hygiene matters more than node hygiene; removing one
CanResetPassword grant or one AdminOn assignment deletes every path
that flowed through it, while renaming accounts or shuffling groups
merely redraws the same map. Learning to see privileges as edges rather
than attributes is the durable skill here, and it costs you nothing
more than a breadth-first search.

## Walking the intended path

Pull /collect/graph.json and read the meta block first: it defines all
four relationship types, and the method notes page pins down how hop
counting works so no question depends on unstated assumptions. For the
shortest-path question, run breadth-first search from dana.reyes rather
than guessing by eye. The chain runs through her reset right over
svc_backup, the service account's interactive session on FILE-01, the
SERVER OPERATORS edge over that host, marko.vukas inside that group,
his reset right over alice.wu, and finally her DOMAIN ADMINS membership,
six hops end to end with no shortcut hiding elsewhere in the data. The
other four questions fall to direct edge scans: exactly one member sits
in DOMAIN ADMINS, two users hold reset rights over svc_backup,
svc_backup's session lands on FILE-01, and SERVER OPERATORS holds
AdminOn there. Submit the five answers as form fields q1 through q5.
Deriving each programmatically is worth the extra ten minutes because
the next real collection will not arrive with a cheat sheet attached.

## Scope

Confine yourself to http://target:8000 within this instance. The
container reaches nothing beyond the lab network: no internet, no host,
no control plane, no neighboring labs. The intended path needs only two
endpoints, /collect/graph.json and /quiz, plus whatever scripting you
prefer for breadth-first search and edge scanning; the front page links
both. Do not probe other ports, attempt to read answers out of server
memory or source, flood the quiz endpoint with guesses, or tamper with
request fields hoping the validator leaks state. The answer space is
small but the point of the room is derivation, not luck, and every
guess-based route wastes your own time. Names and groups printed
anywhere in these rooms are disposable training labels shared across
instances, so never carry them elsewhere, and never point collection
tooling at directories you do not hold written authorization to assess.
Graph techniques belong in labs and authorized engagements first.
