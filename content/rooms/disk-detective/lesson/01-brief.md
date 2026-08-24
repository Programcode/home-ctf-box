# Disk Detective

Disk forensics intimidates people because the tools have acronyms, but
the core artifact is friendlier than it looks: a timeline. When The
Sleuth Kit carves a filesystem it can emit a body file, one row per
named file with every timestamp the filesystem kept, and the mactime
utility turns that into a chronological story. In this room the
Meridian Archive imaging rig produced exactly such a body file from a
compromised host, covering five days around the intrusion. Most of it
is the heartbeat of a healthy machine: logs rotating, caches updating,
configuration files sitting still. Hidden inside that heartbeat is an
attack night, and two artifacts in it matter: something the intruder
tried to erase, and something they left behind to survive reboots.

## What is real here, and what is simulated

No real disk image was carved for this room. The timeline is synthetic
text generated inside your lab container with fixed dates and fixed
files, so every learner sees identical evidence on every run. What is
faithful is the format and the reasoning. Body files really are eleven
pipe-separated columns ending in atime, mtime, ctime, and crtime as raw
epoch seconds, and analysts really do filter them by epoch windows and
sort by time to read an incident unfold. Deleted files really do
survive in timelines with a marker attached to their names, because
deleting unlinks a directory entry while the carve still remembers it,
and attackers really do drop files under /etc/cron.d/ because anything
sitting there executes on schedule without touching user-visible crontabs.
The columns are real; only the compromise is invented.

## Working a timeline like a forensic analyst

Convert first, filter second. Pick the window you care about, turn its
boundaries into epoch seconds once with date, then let awk keep only
rows whose modification-time column falls inside. What remains reads
like a sentence: a tarball lands in /tmp, authorized_keys grows, a
script appears and vanishes, auth.log shrinks to nothing, a helper
binary appears, and a cron drop appears minutes later. Two questions
organize everything else. What did the intruder try to erase? Grep for
the deletion marker and read the name column exactly as printed,
because the marker is part of the evidence string. What did they leave
behind? Filter the same windowed output for the scheduler's directory
and find the file that was written after the noise started. Then do the
step beginners skip: check which finding happened first, because
incident tickets demand chronology and this report desk does too,
rejecting anything filed out of order.

## What you will practice

- Reading body-file columns and filtering by epoch windows.
- Spotting deletion markers and scheduler drops in sorted output.
- Reporting findings in defensible chronological order.

## Scope

Only the case page at `http://target:8000` is in scope. Nothing
outside your lab instance is a target.
