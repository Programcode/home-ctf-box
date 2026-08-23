# scheduled-surprise

Scheduled maintenance runs with someone else's privileges. Root's cron
fires /usr/local/sbin/cleanup.sh every minute. The script itself is
root-owned, but its directory is group-writable for the learners ops
group, and your lab account is in that group. Replacing a file you
cannot edit is still possible when the directory around it is yours to
write.

## What you will practice

- Reading group membership with id and directory modes with ls -ld.
- Finding what cron runs by reading /etc/cron.d.
- Swapping a root-owned script through a writable parent directory and
  waiting out the schedule.

## Scope

Only the box at `ssh://target:22` is in scope. Nothing outside your lab
instance is a target. The hijacked job may only copy files inside this
container; that is exactly what it will do for you.
