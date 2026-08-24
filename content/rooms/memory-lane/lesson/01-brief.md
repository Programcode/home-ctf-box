# Memory Lane

When a workstation is behaving like it has a mind of its own, disk
scanners come up empty more often than anyone likes to admit. Fileless
techniques, deleted droppers, and tampered logs all share one weakness:
if the code is running, it has to exist in memory right now. That is why
incident responders image memory before touching anything else, and why
the first two artifacts out of almost every capture are a process list
snapshot and printable string excerpts. In this room the Meridian
Archive imaging rig pulled exactly that pair from a suspect machine
called workstation-7 before it was reimaged. Somewhere in those rows is
a process that does not belong on any healthy system, and somewhere in
those strings is the address it reports to every few minutes.

## What is real here, and what is simulated

No real memory image was captured and no real malware family is
represented here. Both evidence files are static text written for this
room: the process listing follows ps output conventions so you can
practice column discipline, and the strings excerpt mimics what the
strings utility prints when it walks raw capture bytes, which is why
HTTP headers sit next to library names and configuration fragments.
What is faithful is the tradecraft being modeled. Malware really does
masquerade under desktop-application names while executing from
directories no package manager would ever use, injectors really do leave
their children orphaned when the spawning process exits or is killed,
and implants really do beacon over HTTP whose Host headers survive as
printable text in memory dumps. The artifacts are fake; the reasoning
you apply to them is the same reasoning a responder applies at three in
the morning with production systems on the line.

## Reading a process list like a responder

Work paths first and names never. A process calling itself gnome-something
is interesting only if its executable path is wrong, because names are
cheap for an attacker to choose and directories are not: packaged
software lives under /usr, /bin, /sbin, /lib, or /snap, and user tools
live under home directories, while a dot directory inside /tmp exists
almost exclusively in incident reports. Once the impostor row is found,
read sideways through its parent relationship. Daemons legitimately
parented by init show PPID 1 after adoption, which is normal; what is
not normal is a live process whose parent PID points nowhere in the
dump, because it means the parent died or was hidden between the spawn
and the snapshot, exactly what injection staging looks like. Then take
the strings excerpt and aggregate instead of skimming. Beacon traffic
repeats on a timer, so count Host headers rather than trusting your eye,
and separate the domain that recurs across multiple requests from the
single mention sitting in unrelated package noise. Three findings, one
report, case closed.

## What you will practice

- Judging processes by executable path instead of name.
- Proving a dead-parent anomaly against the full dump.
- Aggregating repeated Host headers into a single C2 verdict.

## Scope

Only the case page at `http://target:8000` is in scope. Nothing
outside your lab instance is a target.
