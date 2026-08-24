# name-resolution

When DNS has no answer, Windows clients shout the question across the
network and trust whoever shouts back first. LLMNR and NBT-NS are those
shouts: link-local name resolution protocols from an era when networks
were small, trusted, and rarely hostile. Because neither protocol
authenticates responders, any host that answers quickly becomes whatever
the asker was looking for, and the authentication handshake that follows
lands in the attacker's hands. This room rebuilds that concept on Linux
with a plain UDP logger standing in for the poisoning responder, so you
can learn the full mechanics, query, claim, capture, verify, without
touching any real network segment or real credential. The scenario is
deliberately concrete: a branch office where one legacy file server is
still resolved by bare name because an old login script says so. Finding
that detail is part of the exercise, and exploiting it is the point.
By the end you will know both why this fallback exists and why so many
defenders switch it off.

## What is real here, and what is simulated

The platform runs Linux containers only, and this room keeps its
simulation honest at every step. The responder-sim is an ordinary
Python program bound to loopback UDP ports 5355 and 137; it receives
plain text queries of the form QRY|PROTO|NAME rather than real LLMNR or
NBT-NS frames. When you query the one name it claims, it answers with a
blob labeled NTLMv2-SIM whose value comes from HMAC-SHA256 over a fixed
seed, which makes it deterministic for the room yet entirely unrelated
to any password, hash, or account that ever existed. No packet leaves
the container's loopback interface at any point. The capture log lands
in /srv/public, a world-readable directory standing in for the share a
real attacker-facing responder would expose, and a fuller query log
lives under /var/log/responder-sim for correlation practice. The SSH
login, file reads, UDP exchange, and HTTP submission are genuinely
happening Unix and web mechanics; only the Windows name-resolution
layer is pretend, and every banner, README, page, and response header
says exactly that.

## Why poisoning works

The failure is architectural rather than incidental. Legacy fallback
protocols were designed for convenience: if unicast DNS stays silent,
ask the whole segment, then accept the fastest answer without verifying
who answered or why they knew. No signature covers the response, so
whichever host replies first wins the client's trust, and with it
whatever the client sends next, most usefully an authentication
handshake aimed at what it believes is a file server. Attackers do not
need to force this traffic to flow, since background chatter like
printer discovery, file-share lookups, and software update checks
supplies queries continuously on a typical Windows network. The durable
defenses are structural rather than detective: disable LLMNR and NBT-NS
where business processes allow it, require SMB signing and LDAP signing
so a captured handshake loses its resale value, segment networks so
broadcast domains stay small, and alert on name-conflict storms that
indicate someone is answering everything. Each defense removes value
from the capture instead of trying to make shouting polite.

## Walking the intended path

Log in as learner and read before you type anything into a client. The
tools README explains the client syntax, names both log locations, and
warns that only claimed names answer. The simulated site inventory at
/srv/public/network-inventory.txt describes four hosts, and exactly one
of them, FILESRV01, still gets resolved by bare name because a finance
department login script maps its share directly. That detail is your
targeting hint and mirrors how attackers read naming conventions before
choosing what to impersonate. Send queries for two or three inventory
names with namesim_query.py and watch the others draw silence; the
responder answers only the name it was told to claim, which shows how
selective a real poisoning attempt looks inside a packet capture. The
winning query prints a reply containing the SIM-HASH blob and appends a
capture block to /srv/public/responder-capture.log. Copy the complete
value from either place and submit it to the checker page on port 8000,
which verifies the exact string and hands back the room flag.

## Scope

Confine yourself to ssh://target:22 and http://target:8000 inside this
instance. The container reaches nothing beyond the lab network: no
internet, no host, no control plane, no neighboring labs. The exercise
needs nothing more than the provided client, two log files, one
inventory note, and the checker form; do not attack sshd itself, do not
send raw packets anywhere except the documented loopback ports, and do
not attempt to brute-force the checker's accepted value. None of that
is necessary and none of it is permitted by the scope declaration.
Credentials and blobs printed anywhere in these rooms are disposable
training labels shared across instances, so never carry them to systems
outside the lab, and never run anything resembling this technique
against networks you do not own and have written permission to test.
Poisoning concepts belong in labs like this one and in authorized
assessments, nowhere else. If a technique only works against people
who never agreed to be tested, that is your answer about where it
belongs.
