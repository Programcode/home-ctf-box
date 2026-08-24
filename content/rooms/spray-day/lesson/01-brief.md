# spray-day

Password spraying works because it inverts the economics of guessing.
Brute force spends many attempts on one account and runs straight into
the lockout counter; spraying spends one attempt on many accounts and
stays invisible to any per-account tripwire. Real campaigns against
mail providers, VPN portals, and cloud tenants follow exactly this
pattern, because a single well-chosen password usually works for a
handful of users out of hundreds. This room is a fictional staff portal
built to teach that discipline honestly: the lockout policy actually
locks, the enumeration oracle actually answers, the artifacts actually
assemble into one working password, and the difference between careful
spraying and clumsy guessing shows up directly in whether accounts lock
while you work. The portal is deliberately small, so every moving part
of the attack stays visible and nothing hides behind framework magic.
Read the pages, respect the counter, and the room rewards you; spray
carelessly and the lockout message becomes your teacher instead.

## What is real here, and what is simulated

Everything visible is a Flask application holding its state in memory,
running as an unprivileged user in a locked-down container with no
capabilities at all. The eleven directory entries are fictional people;
seven have working sign-ins and four exist only on paper. The reset
form is a genuine enumeration oracle: its two answers differ for real
mailboxes and published decoys, which is precisely the information leak
real environments expose through password-reset flows, login hints, and
directory listings. The lockout logic genuinely counts consecutive
failures per existing account and genuinely blocks sign-ins for ninety
seconds once three stack up, so clumsy testing has visible costs inside
the room. The seasonal password RiverbankOtter07 exists only in this
container's process memory and comes from the scheme documented on the
policy page plus two facts split across that page and the facilities
memo. No mail server, identity provider, or real credential exists
anywhere here, every page carries a simulation notice, and nothing you
do can affect anything beyond this disposable instance.

## Why spraying beats naive brute force

The math is uncomfortable for defenders. If a site allows three bad
attempts before locking an account, an attacker who tries forty
passwords against one user gets locked out after three. The same
attacker armed with one strong candidate guess and four hundred
usernames gets four hundred attempts at the exact credential pattern
people actually choose, and no individual account ever shows more than
a single failure, so no lockout fires anywhere. Enumeration makes it
worse still: reset forms, directory pages, and login error messages
routinely sort live accounts from dead ones before the first password
is tried, which is why this room makes you enumerate first. Defenses
that work reduce the value of each guess rather than counting failures
louder: screening passwords against breach corpora at set time,
requiring longer minimum lengths so seasonal word schemes die, rolling
out phishing resistant second factors, and making every authentication
error message identical so the oracle this room deliberately hands you
disappears. Notice how each measure attacks the economics instead of
the symptom.

## Walking the intended path

Start at the front page and read the policy before touching the login
form; it states the three-attempt limit, the ninety second lockout, and
the seasonal scheme, then hands you the theme word Riverbank. Pull the
staff directory next and feed all eleven addresses to the reset form.
Seven answers say a reset was queued while four say no such mailbox
exists; keep the seven, because spraying dead addresses teaches nothing
and wastes attempts. The facilities memo completes the assembly with
the mascot Otter and building number 07, giving RiverbankOtter07,
capitalized exactly as printed with no separators. Now spray with
restraint: submit the password to each confirmed mailbox once each,
never twice, and stop at the first success. One of them opens the
welcome page and prints your session flag. Count what happened along
the way: at most one failed attempt per account, zero lockouts
triggered, full access gained, which is the entire point of the
technique and the reason it deserves respect.

## Scope

Confine yourself to http://target:8000 within this instance. The
container reaches nothing beyond the lab network: no internet, no host,
no control plane, no neighboring labs. The intended path needs only the
reset form, three public pages, and the sign-in form, all documented on
the front page. Do not attempt request smuggling, parallel flooding to
dodge the lockout timer, brute force of the flag format, or probing of
other ports; none of that teaches the lesson, none of it is necessary,
and all of it falls outside the declared scope. Every name, mailbox,
and password printed in these rooms is disposable training data shared
across instances, so never carry it elsewhere, and never practice
spraying against systems you do not own and are not explicitly
authorized to test. The technique is legal only inside labs like this
one and written engagements; everywhere else it is an attack, and
treating that line as part of the lesson is the point of this room.
