# service-please

Long-running services read configuration, and on this box the reading
happens with a shell dot command inside a root-owned loop. That turns
every cycle into an invitation: whatever the config says, root types.
The file is world writable, so anyone logged in can write the next line
root will execute.

## What you will practice

- Reading ps output to find service processes that belong to root.
- Tracing a running script back to the files it consumes and checking
  their permissions.
- Appending to a configuration you cannot own but can edit, then
  waiting for the service schedule to act on your behalf.

## The scenario

The orders-api team ships a tiny supervisor called app-runner.sh. It
sources /etc/app/env every thirty seconds so operators can adjust
settings without restarting anything. The convenience stopped there:
the config shipped as -rw-rw-rw-, and nobody noticed because the
application still runs.

## How to work it

Confirm the process and its rhythm before touching anything. Read the
script so your edit lands where execution actually happens. Two lines
in the config are enough for this room: one copies /root/flag.txt to
/tmp/flag, the other makes that copy readable. The next cycle takes at
most about thirty seconds, so poll rather than assume.

## Scope

Only the box at `ssh://target:22` is in scope. Nothing outside your lab
instance is a target. Log in as learner with password learner. The
supervisor may only copy files within this container, and that is all
it takes here.
