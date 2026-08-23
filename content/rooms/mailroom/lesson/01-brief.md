# Mailroom

Meridian Freight runs a staff webmail portal called MailGate, and its
admin status page is more talkative than it should be. Real mail
servers expose a VRFY command during the SMTP handshake: you send a
username and the server tells you whether a mailbox answers to that
name. It was meant for delivery troubleshooting, and it turned out to
be one of the cheapest enumeration oracles ever shipped. This room
recreates that behavior as an HTTP endpoint so you can practice
against it without a mail daemon in the loop. Every page in the portal
carries a simulation notice saying exactly that, because we want you
to keep the boundary between this lab and real infrastructure sharp.

## What you will practice

- Reading an admin page for operational intelligence before touching
  any protocol. The status panel documents the legacy endpoint at
  `/api/vrfy`, shows its response shape, and mentions an open change
  ticket that leaks the temporary mailbox password. Attackers read
  pages like this carefully; defenders should too.
- Turning a yes-or-no oracle into a user list. You will send candidate
  usernames and sort responses by code: 250 with a GECOS field means
  the mailbox exists, 550 means it does not. Distinguishable failure
  messages are the same weakness behind user enumeration on login
  pages and password reset forms.
- Testing one credential across every account you confirmed. The
  ticket admits all staff mailboxes share `spring-meadow-42` until
  rotation week ends. That is textbook password reuse: one leak
  becomes many compromises, which is why rotation windows are
  dangerous and unique passwords per account are policy almost
  everywhere.

The flag sits in exactly one inbox, Jordan Harper's second message.
The other confirmed mailboxes hold harmless filler so you learn to
walk your enumerated list instead of guessing where treasure hides.

## Scope

Only the portal at `http://target:8000` is in scope. Nothing in this
room speaks SMTP; there is no daemon to connect a mail client to, and
no packet leaves the lab network. Treat every credential you find here
as fictional. If a string like `spring-meadow-42` ever looks familiar
from a system you actually administer, treat that as a coincidence to
fix, not a pattern to copy.
