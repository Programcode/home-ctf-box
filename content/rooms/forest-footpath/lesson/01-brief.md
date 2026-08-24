# forest-footpath

Active Directory forests are held together by trusts, and most breaches
that cross domain boundaries ride a trust rather than break one. This
room teaches you to read a trust relationship and use exactly what it
grants, nothing more. Two domains, child.corp and parent.corp, sit in
the same simulated forest. You hold Domain Admins in the child. The
trust document on the child admits what seasoned AD operators already
know: the parent-child link inside a forest is transitive, which means
your child-domain power reaches into the parent's enterprise scope
without a single password ever being stolen from the parent side. You
will authenticate on the child API, carry its token across the boundary
through the documented exchange endpoint, and pull the flag from
enterprise scope. Before touching anything, notice how much of this
room is reading: the entire attack path is written down for anyone who
asks the right endpoint the right question, which is uncomfortably
often true of real environments too.

## Why transitivity changes everything

A trust answers one question: can principals from domain A
authenticate to resources in domain B? Direction says who can go where.
Transitivity says whether a trust chains through intermediaries.
Within a single forest, every child domain connects to its parent, and
because those links are transitive by design, any principal in any
child domain has a route to any other domain in the forest. That is
not a misconfiguration; it is how Microsoft designed forests so an
enterprise admin could administer everything from one place. The
security consequence deserves emphasis: compromising one child domain
effectively compromises the forest, because the child's own
administrators can mint identities the rest of the forest will honor.
Attackers exploit this property constantly, and defenders need it
burned into memory when they decide how much privilege a child domain
admin really holds. When you read a trust document later in your
career, transitive: true should make you sit up straight and ask who
else can already walk through that door.

## Reading the trust before you walk it

Disciplined operators enumerate before they authenticate anywhere new,
and that habit maps directly onto this room's mechanics. Fetching
/trusts on child.corp first gives you direction, transitivity, and a
notes field spelling out the practical consequence: tokens the child
mints for DA-child members are accepted at the parent's exchange
endpoint. Only after the picture is clear do you authenticate with
learner/learner, receive a childtok bearer token, POST it to
/trust-exchange on the parent, and present the returned parenttok
against /enterprise/path. Each hop fails closed if you skip or
reorder one, so the chain itself teaches the sequence an attacker must
follow and a defender must watch for. Treat every JSON field you read
as reconnaissance data rather than decoration: the endpoints block in
the trust document names exactly the two routes you will chain, which
mirrors how real AD enumeration tools surface trust metadata before
anyone attempts a cross-domain move. Write each token down as it is
minted so the final request reads like the summary of your own notes.

## What is real here, and what is simulated

Plain disclosure: there is no Windows kernel, no Kerberos realm, and
no domain controller in this lab. One Linux container runs two small
JSON APIs on separate loopback ports behind a single front controller
on port 8000 that routes by Host header, the same way a reverse proxy
fronts several internal sites. Tokens are short HMAC labels standing
in for Kerberos tickets, and the exchange endpoint stands in for the
trust validation a real domain controller performs when it decides
whether a foreign realm's ticket deserves service access. Those
simplifications remove protocol noise without removing judgment: the
mechanics you practice here, reading trust direction and transitivity,
chaining credentials across a boundary instead of guessing at it, and
treating documentation as recon material, transfer unchanged to real
environments where the same properties decide whether one compromised
branch office costs you the whole enterprise. The labels are props;
the reasoning you practice on them is not.

## Scope

Only http://target:8000 is in scope, and both simulated domains live
behind it, selected purely by Host header. Nothing outside your own
lab instance is a target, and the container has no outbound network
access anyway. The intended outcome is one flag pulled from the
parent's enterprise path using a token chain you assembled yourself,
and nothing else beyond that single artifact. If you find yourself reaching for credentials other
than learner/learner on the child API, you have wandered off the
intended path, so backtrack to the trust document and reread what it
promises. Every capability you need was disclosed somewhere on the
box, which is itself the lesson: attackers rarely invent access, they
read what the environment volunteers and follow it politely until the
crown jewels answer, so make reading the first tool you reach for here.
The container regenerates its state on every boot, so exploring boldly
costs nothing and teaches more than caution ever will.
