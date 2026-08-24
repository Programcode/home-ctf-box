# Services Everywhere

Real machines rarely run exactly one service, and they almost never
run only the services their documentation mentions. The appliance in
front of you presents a quiet SSH port, but a sweep of its higher
ports finds two more listeners: a community file drop that predates
the current admin team, and a management console for the webapp this
host exists to serve. Boxes like this are the classic first target in
vulnerable-machine training ranges inspired by multi-service images:
the way in is rarely the front door, it is the forgotten side entrance
nobody cleaned up before the last reorganization.

## What you will practice

The first skill is protocol identification by conversation. The 2121
service will not announce itself as any well-known daemon; you connect,
read its banner, and learn its small command set from what it tells
you. This mirrors how real enumeration tools fingerprint unknown
listeners: send something reasonable, watch what comes back, adjust.
You will drive the service with a raw socket rather than a heavy FTP
client, because the fastest way to understand a line protocol is to
type it yourself.

The second skill is chaining a low-value leak into real access. The
file drop accepts anonymous logins because once upon a time that was
convenient. Inside sits deployment paperwork with live manager
credentials written into a note. Nothing about that note is encrypted
or hidden; its power comes entirely from being reachable without
authentication. When you find credentials on an engagement, the
question is never whether they look important, it is which doors they
open. You will answer that question by logging into the 8080 console
and reading what it lets you do.

The third skill is reading an interface before acting on it. The
manager console documents exactly one capability: deploying a named
artifact that republishes a verification copy of the application flag
into the web tree. That is deliberately safe and deliberately narrow.
Your job is to notice the shape of the action, trigger it correctly,
and collect what it published at the path it names. Careful operators
confirm what an action does before pressing the button; this room
rewards the same habit.

## Scope

Only the appliance itself is in scope: SSH on port 22, the file drop
on TCP 2121, and the HTTP console on 8080 of your own lab instance.
Nothing outside your instance is a target and the box reaches out to
nothing, so every byte you send stays inside your session's private
network. Treat this boundary the way you would treat a signed rules
of engagement document on a real engagement: the credentials you
recover here work only inside this disposable container, and reusing
them anywhere else would be both pointless and wrong.

Know what the deploy action really does before you trigger it. It
copies one flag string from an application-private file into the
published web tree, nothing more. There is no command execution in
this image, no shell behind the console, and no state that survives
the container being destroyed. When you finish, verify your own work:
the flag you submit must have traveled the full intended path from
anonymous share, through leaked credentials, through the documented
deploy action, to the published page. A flag obtained any other way
means you skipped the skills this room exists to build.
