# gpo-gone-wrong

Group Policy is a distribution system for code execution. Every
scheduled task, startup script, and immediate task a GPO defines gets
read from SYSVOL by machines across the domain and run under
authoritative accounts, SYSTEM on the workstation side most commonly.
SYSVOL is readable by every authenticated user, because policy has to
be, which means any domain account can enumerate exactly what executes
where and as whom. When one of those definitions points at a script
sitting in a folder the wrong group can write to, the attacker no
longer needs to touch the GPO at all; they just edit what policy will
run next cycle and let the domain's own machinery execute their code
with maximum privileges. This room models that whole chain on a Linux
box: find the policy store, read the task definitions, spot which one
runs from writable ground, edit it, and wait out the loop.

## What is real here, and what is simulated

The room is one disposable Debian container reached over SSH as
learner with password learner. A simulated SYSVOL tree lives at
/srv/sysvol-sim with two policy GUID folders: one holds inert security
settings, the other defines scheduled tasks in Machine/Preferences/
Tasks/tasks.xml with Command entries, runAs attributes reading
NT AUTHORITY\\SYSTEM, and interval values. A stdlib Python runner
started by root parses those XML files exactly the way Group Policy
processing reads task definitions from SYSVOL and executes each
Command every 30 seconds. That runner is the honest stand-in for the
Windows Task Scheduler applying policy, not an emulation of Windows
itself; nothing here speaks Active Directory or SMB. Two tasks exist:
Audit Stamp runs /usr/local/sbin/audit-stamp.sh from a locked-down
path, while Cache Refresh runs /srv/gpo-scripts/cache-refresh.sh from
a directory owned root:gpo-editors with mode 775, and the learner
account sits in gpo-editors. Escalation stays inside the container:
the hijacked task only ever copies /root/flag.txt to /tmp within this
disposable filesystem. The elevated privilege profile exists solely
because sshd needs its bounded capability set for privilege
separation; sessions themselves drop to unprivileged uid 1000.

## Why SYSVOL turns policy into an attack surface

Three facts combine into this technique. Policy content must be
readable by everything it applies to, so reconnaissance costs one
directory listing. Task definitions reference scripts by path, so the
security of the whole arrangement reduces to the permissions of
whatever directories those paths traverse. And execution recurs on
the domain's schedule, so an edit made once keeps paying out until
someone notices. Real-world attackers treat SYSVOL as a map of
guaranteed code execution and hunt for GPO-created tasks whose targets
land in world- or group-writable locations, then ride the existing
schedule instead of planting their own persistence that defenders
would flag. Defenders respond from both ends: audit GPO-defined tasks
for where their Commands live and who can write there, using
reporting tools rather than manual shares browsing, and lock down the
script trees policy points into, since a task definition is only ever
as trustworthy as the least privileged writer above its target file.
The room shows the contrast directly: the audit script survives your
group membership untouched while the cache script bends immediately.

## Walking the intended path

SSH in as learner and run id to confirm membership in gpo-editors.
Enumerate the policy store with find /srv/sysvol-sim -name "*.xml"
and read both hits. The security-settings XML teaches you what a
policy without tasks looks like; tasks.xml lists two scheduled tasks
with their runAs principals and intervals. Cross-reference each
Command against disk permissions: ls -ld /srv/gpo-scripts shows
drwxrwxr-x root:gpo-editors, and ls -l reveals cache-refresh.sh is
775 owned by root:gpo-editors, so you can rewrite its contents
directly without needing the directory trick, though the directory
write would work equally well. Replace the script body with two lines,
cp /root/flag.txt /tmp/flag and chmod 644 /tmp/flag, keeping it
executable. Then wait up to about 70 seconds for the next 30-second
policy tick and cat /tmp/flag, which now contains FLAG{...}. Submit
that value. If nothing lands, re-read the script you wrote; the most
common failure is a typo in the copy line, which the policy loop will
faithfully fail to act on every half minute.

## Scope

Confine yourself to ssh://target:22 within this instance as the
learner account. The container reaches nothing beyond the lab
network: no internet, no host, no control plane, no neighboring labs.
Everything the intended path needs sits on the box: the simulated
SYSVOL tree, the script folders, the policy loop, and the root flag.
Do not attempt to break out of the container, attack sshd itself,
brute-force other accounts, or modify the policy XML to point at new
targets; none of it is necessary and none of it teaches the technique
this room exists to teach. The policy loop reads only the simulated
SYSVOL tree, so editing XML elsewhere gains nothing anyway.
Credentials printed here are disposable training labels shared across
instances, never valid anywhere else.
The same caution scales up outside the lab: editing scripts that
privileged automation runs is unauthorized access wherever you lack
written permission, and the fact that a directory lets you does not
mean the owner does.
