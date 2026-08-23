# container-window

This room is honest with you from the first line: the box you log into
is itself a container. The classic reflex is to hunt for a docker
socket, so look for one, and watch the lookup fail. Real environments
do not always leak their escape hatches, and this lab models the host
relationship a different way, through delegated trust.

## What you will practice

- Testing an assumed escape surface, reading the negative result, and
  moving on instead of forcing it.
- Reading a sudoers drop-in to learn precisely what your account may
  run as root and why.
- Driving a restricted inspection tool: enumerate its subcommands, stay
  inside its allowed root, and pull the file that only it can open.

## The scenario

In production fleets, membership in the host docker group is equivalent
to root on that host because the socket speaks for the daemon. This lab
keeps the lesson and drops the infrastructure. Your learner account
holds a NOPASSWD sudo grant for /usr/local/bin/container-inspect, a
read-only utility whose ls and cat subcommands serve exactly one tree:
/hostsim, which stands in for an attached host filesystem. Inside that
tree sits /hostsim/root/flag.txt at mode 600, invisible to direct reads
by your uid.

## How to work it

Start where honesty starts: check /var/run/docker.sock and read the
error. Then run sudo -l, study the granted tool with cat before using
it, and walk its info, ls, and cat subcommands down to
/hostsim/root/flag.txt. Submit the FLAG value it prints. If a path
outside /hostsim tempts you, remember the tool refuses it by design,
and nothing else on this box needs escaping.

## Scope

Only the box at `ssh://target:22` is in scope. Nothing outside your lab
instance is a target. Log in as learner with password learner. The
inspection tool may read only inside this container; no real host is
attached.
