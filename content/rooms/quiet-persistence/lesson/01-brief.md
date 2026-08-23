# Quiet Persistence

Attackers rarely leave through the front door; they also rarely leave
without leaving footprints. This box has been "compromised" in the
gentlest possible way: someone planted four persistence mechanisms
across the usual hiding spots. Nothing hostile runs here, and we say
so up front. The cron entry never fires because no cron daemon is
installed, the systemd unit never starts because no init exists in a
container, the modified shell init waits on a login that will not
happen, and the loop script does exactly one thing: append timestamped
lines to /tmp/.beacon.log. Your job is to find all four, not to fight
them.

## What you will practice

- Sweeping locations in a fixed order so nothing gets skipped:
  cron drop-ins under /etc/cron.d, shell init files in every home
  directory, site-local admin binaries under /usr/local/sbin, and
  custom units under /etc/systemd/system. Method beats inspiration;
  an analyst who sweeps the same list every time finds things that
  clever analysts miss on busy days.
- Correlating indicators across finds. The artifacts share a family
  resemblance by design: system-sync schedules sysmon-helper,
  sysmon.service restarts sysmon-helper always, and both it and the
  deploy account's .bashrc write to /tmp/.beacon.log. One indicator
  discovered late confirms everything found early, which is how real
  timelines come together.
- Reporting findings the way incident tickets need them: exact full
  paths, submitted to the box's own verification endpoint at
  http://127.0.0.1:8000/api/report. Vague findings fail; precise ones
  return the flag along with a verdict you can stand behind.

## An honest note about the threat model

Every mechanism here is inert theater with honest plumbing: the loop
prints to a local file, nothing opens network sockets beyond sshd and
the loopback report API, and no payload of any kind exists in the
image. That restraint is deliberate. Learning to hunt persistence
does not require live malware, and keeping the room clean means the
worst thing that can happen from replaying these commands is that
your own log grows.

## Scope

Only `ssh://target:22` inside this lab container is in scope, as the
analyst account. The reporting endpoint is loopback-only and reachable
from your SSH session on the box itself. Everything you touch here is
fictional evidence; treat the workflow, not the artifacts, as the
take-home.
