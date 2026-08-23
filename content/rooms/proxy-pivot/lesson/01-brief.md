# Proxy Pivot

You have valid SSH credentials for a lab box, and that is the whole
attack surface you get. Somewhere on that box an admin console is
running, but it never left the loopback interface. From your
workstation, 127.0.0.1 means your own machine; the target's 127.0.0.1
is a different address entirely. That gap between two loopbacks is
what pivoting crosses.

## What you will practice

- Confirming what a service is bound to before assuming reachability.
  Inside the target, `ss -tln` will show the console on
  127.0.0.1:9001 and sshd on 0.0.0.0:22. The bind address is the
  access control here.
- Building a local forward with `ssh -L`. The command opens a port on
  your workstation; every byte written there travels inside the SSH
  channel and exits on the far side toward a destination of your
  choosing, in this case the console's own loopback.
- Understanding what SOCKS proxies and tunnel tools do underneath.
  The automated solver skips the ssh binary entirely and opens the
  same relay with paramiko's direct-tcpip channel, writing raw HTTP
  request bytes into it. Same mechanism, no magic: an authenticated
  channel plus a relay.

This is the honest version of pivoting: one hop, explicit credentials,
a service that was never meant to face a network. Multi-hop pivots,
SOCKS chains, and port forwards through jump hosts are all this same
pattern repeated.

## Scope

Only the box at `ssh://target:22` is in scope, including services
reached through authenticated tunnels to it. Nothing outside your lab
instance is a target.
