# service-accounted

On a real Windows machine the Service Control Manager owns a list of
every installed service: its name, its account, and above all the
binPath, the executable it launches. Services rarely run as ordinary
users; they run as LocalSystem or another privileged account, which
means whatever sits at that path executes with enormous power. The
classic abuse follows directly from two facts stacked on top of each
other: if you can control the file at a service's binPath, or plant a
file where an unquoted or misconfigured path resolves first, the next
service start runs your code as SYSTEM. Defenders look for exactly
this pairing during audits, and attackers have used it for decades
because administrators keep leaving writable directories underneath
privileged binaries. This room compresses that whole story into one
small box so you can feel both halves of it, the audit and the abuse,
within half an hour.

## What is real here, and what is simulated

Plainly stated: there is no Windows Service Control Manager in this
lab, because the platform only runs Linux containers. What stands in
for it is honest about its seams. The service list lives in a
root-owned JSON file at /opt/services/services.json whose entries
carry Windows-style binPath strings alongside the payload this box
actually executes, and a root shell loop re-runs every Running
service's payload every 30 seconds where the SCM would launch or
restart binaries. The permissions underneath are entirely real Unix
permissions doing real work: the database is world-readable like
service enumeration on Windows, the payloads run as root like
LocalSystem services, and the updater directory is genuinely writable
by your group. When you append to that payload and the loop picks up
your line as root, nothing about the privilege boundary is faked.
Only the dressing around it is labeled simulation.

## Reading the service audit trail

Start where any auditor starts, at the inventory. The JSON database
is deliberately readable by everyone, mirroring how cheap it is to
list services on Windows with sc query or Get-Service before any
escalation attempt. Each entry gives you three things worth
cross-referencing: the account it would run under, the binPath it
claims, and the linux_sim_path it actually runs in this simulation.
The audit question is always the same regardless of operating system:
for every privileged executable, who can write to its directory? On
Windows that means checking ACLs on folders like Program Files; here
it means running ls -ld on each parent directory and comparing the
owner group against your own id output. Two of the three services sit
under locked-down directories nobody but root can touch. One does
not, and the moment directory permissions contradict the privilege of
the process executing from them, you have found the finding.

## Turning the finding into the flag

Finding a writable payload directory is the audit half; acting on it
is the exploitation half, and here the room lets you do both safely.
The UpdateHelperSvc entry points into /opt/services/updater/bin, a
directory your learners group may write, and its uhelper.sh runs as
root on every 30-second pass of the simulated scheduler. Appending a
line to that script is exactly the move that mirrors dropping code
where a SYSTEM service will execute it. Choose your appended command
so the result lands somewhere you can read, then respect the rhythm
of the scheduler: the loop fires on its own clock, so poll rather
than assume instant results. When the copy completes, read the output
file and submit the flag value it contains. On a real engagement the
same patience applies to service restarts, which admins trigger or
timers eventually force; here the 30-second tick plays that role.

## Scope

Work only against ssh://target:22 using the learner credentials this
room published. The container has no route to the internet, the
host, other labs, or the control plane, and nothing outside your own
instance is ever a target. The intended action is one small edit to
one payload inside this box, producing one readable copy of this
box's own flag file; resist the urge to get creative with the root
loop beyond that, since everything you could break belongs to a
shared training environment. Lab credentials exist so beginners can
log in, not because they carry value anywhere else, and reusing them
on real systems is the fastest way to turn practice into incident
response. If you find yourself wanting a capability the room has not
declared, treat that as a sign the intended path lies elsewhere.
