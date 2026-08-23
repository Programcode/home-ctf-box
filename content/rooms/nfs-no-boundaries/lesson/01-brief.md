# nfs-no-boundaries

NFS trusts user IDs the way a doorman trusts printed name badges. With
the default root_squash setting that trust is bounded: a remote client
claiming uid 0 gets squashed to an unprivileged account before it
touches the export. Flip one option to no_root_squash and the bound
disappears. This room teaches what disappears with it, using one box
instead of a storage fleet.

## What you will practice

- Reading an exports file and predicting what each option grants.
- Hunting for SUID files in places where world-writable meets
  root-owned.
- Separating the parts of a classic attack that this lab simulates from
  the parts it runs for real.

## The scenario, simulated versus real

The real attack needs two machines. An attacker controls a client,
mounts an export exported with rw and no_root_squash, and because their
root is not squashed they can write files owned by uid 0 into the
share. They plant a tiny binary with the setuid bit set. Later, any
user on any client mounting that share executes it, and the kernel
honors the bit: the process runs as root.

This lab collapses both machines into one container. There is no NFS
server here, no mount daemon, and nothing network-mounted; /etc/exports
survives as documentation of the misconfiguration, and /srv/share is an
ordinary directory at mode 777 standing in for the writable export.
What the lab does run for real is the payload side: a scheduled sync
job running as root stages snapshot-recover into the share carrying a
genuine SUID bit, exactly as an attacker's planted binary would arrive.
Executing it gives you a privileged shell command.

## How to work it

Read the export line first so the lesson has context. Then enumerate:
world-writable directory plus SUID file is a pattern worth memorizing.
Confirm the helper's owner and mode before executing it, run it once
with id to see whose credentials it uses, and then aim it at
/root/flag.txt. Submit the FLAG value it prints.

## Scope

Only the box at `ssh://target:22` is in scope. Nothing outside your lab
instance is a target. Log in as learner with password learner. No
network filesystem exists in this lab; everything happens inside the
one container.
