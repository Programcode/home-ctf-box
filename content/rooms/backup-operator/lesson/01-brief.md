# backup-operator

Every directory service has a handful of groups whose names sound
harmless and whose grants are anything but. Backup Operators is the
classic Windows example. Backups must read every file to do their job,
so Windows ships a privilege, SeBackupPrivilege, that overrides file
ACLs entirely. Hand someone that privilege and you have handed them
read access to everything: every payroll spreadsheet, every database
dump, every secret sitting on disk waiting for someone with a reason
to open it. This room puts you in exactly that position on a Linux
box so the underlying lesson sticks without needing a Windows estate,
and so you learn to treat backup-style grants as what they are: a
standing offer of universal read access that most organizations hand
out far more casually than they would ever hand out a password.

## Why backup privilege is total read access

Think about what a backup program must be able to do. It walks the
whole filesystem and reads each file, including files owned by other
users, files protected by ACLs, locked databases, registry hives mid-
write. If an ACL could refuse it, backups would be incomplete and
restores untrustworthy, so the platform provides an override instead.
Membership in the backup group therefore becomes a standing grant of
universal read, and the audit trail of who holds it matters more than
almost any other group membership in the directory. Attackers who
obtain any backup-capable credential exploit exactly this: no
escalation dance required, just run the sanctioned tooling against
the file you want and let the platform's own trust do the work. The
defensive takeaway is equally direct: inventory backup-style
privileges constantly, keep them off workstations and administrators'
daily accounts, and alert on their use because legitimate use is rare
and illegitimate use is catastrophic.

## How this room simulates the privilege

One Linux container stands in for the domain-joined host. Your account
is an ordinary user with one extra membership: group backup. That
group's entire power is the ability to execute
/usr/local/bin/disk-shadow-sim, a small compiled helper owned by root
with the SUID bit set and mode 4750, meaning only backup members may
run it and when they do it executes as root for its duration. Its
single operation is copying a named source file to a destination under
/tmp, which mirrors how real shadow-copy workflows stage data before
archival or exfiltration. Because the helper runs as root, the source
opens without regard to its permissions; that behavior is the
emulation of SeBackupPrivilege in its purest form, one tool, one
purpose, total read. Read /etc/backup-policy.txt on the box before you
use it; the note explains the mapping from Windows privilege to Linux
mechanism in the same terms an incident responder would use when
explaining why a Backup Operators membership belongs on the watchlist.

## Walking the room

Start by proving the premise rather than assuming it. `id -nG` shows
your memberships, and ls -l on the helper shows the s bit plus the
backup group ownership, which together explain why executing it
elevates you for exactly as long as it runs. Then aim the grant at the
target: stage /root/flag.txt into /tmp with disk-shadow-sim and read
the staged copy with cat. Notice what did not happen here: no password
guessing, no hash cracking, no scheduler race, no kernel exploit. The
room is deliberately boring once you understand the grant, because
that understanding is precisely what transfers. Whenever you land in a
new environment, enumerate backup-style groups first, check which
binaries their members alone may execute, and treat those members as
readers of everything until proven otherwise. Boring rooms teach the
habits that make hard rooms survivable, and this one also plants a
question worth carrying home: who in your own organization can read
everything, and when did anyone last check?

## Scope

Only ssh://target:22 is in scope, reached as learner/learner inside
your own lab instance. The intended abuse is one copy of this
container's own flag file into /tmp, nothing more, and the helper
refuses destinations outside /tmp by design so the blast radius of any
experiment stays inside the box. Nothing you do here can affect other
labs, the host, or anything beyond your instance, which frees you to
inspect the mechanism thoroughly rather than carefully: read the C
source comments in the image documentation if you want, run the helper
against files you cannot read and watch it succeed, then run it
against a path outside /tmp and watch it refuse. Both behaviors are
the lesson working as intended, and both reward learners who poke at
boundaries instead of trusting descriptions of them. The box rebuilds
its flag and policy files on every boot, so there is no wrong way to
explore it more than once.
