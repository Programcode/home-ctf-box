# Namespace Escape Plan

Sandboxes earn trust only when their boundaries hold. This box drops
every SSH session into a chroot sandbox at /jail using a small
elevated helper called jailctl. The same helper offers an
administrative subcommand, `jailctl chroot NEWROOT [COMMAND...]`,
which is where the trouble starts. The helper performs the chroot but
never moves its working directory under the new root, and a process
whose cwd lies above its own root can walk straight out with relative
paths. You will exploit exactly that, with commands you type yourself.

## What you will practice

- Confirming a boundary before attacking it. From inside the jail,
  `ls /` shows only the sandbox contents and `cat /flag.txt` returns
  FLAG{JAILDEC0YCOPY0000000}, a decoy we planted on purpose. When you
  later see a flag at the same path, you will know to ask which side
  of the boundary it came from, because identical paths mean nothing
  across roots.
- Executing the classic double-chroot escape in two deliberate steps.
  First, stage busybox inside a fresh directory such as /tmp/esc,
  because once the root changes, exec resolves every path against the
  new one. Second, run `jailctl chroot /tmp/esc ...`: the process now
  lives under /jail/tmp/esc while its cwd remains stranded at
  /home/learner, outside the new root. Three `..` hops from there
  reach the real filesystem root. The helper plants an elevated stub
  of itself inside each root it enters (you will see it as /.jt), and
  that stub performs the second chroot onto "." once you have climbed,
  swapping the sandbox for the real thing.
- Explaining the fixes, which matter more than the trick. coreutils'
  chroot calls chdir("/") immediately after chroot() precisely to
  strand the cwd under the new root and kill this climb. The helper
  also keeps re-arming itself: every root it enters gets a fresh
  setuid stub, the same pattern as a sudo-wrapped helper, which is
  what lets the second step regain capabilities at all. The deeper
  lesson is structural: handing an untrusted user any privileged
  helper that can chroot somewhere of their choosing defeats the
  sandbox by design, no memory corruption required.

## An honest note about isolation

This room simulates a misconfigured namespace with a chroot, not a
container runtime breakout. The escape crosses one boundary inside
the lab container; the container's own namespace stays intact the
whole time, so nothing here leaves the box. Real container escapes
add kernel and capability subtleties on top, and the curriculum covers
those separately. The double-chroot technique itself is period
correct: administrators have used it, and misconfigured SUID helpers
have enabled it, for decades.

## Scope

Only `ssh://target:22` inside this lab container is in scope, as the
learner account. Do not attempt chroot experiments on machines you do
not own; outside a lab, this technique crosses from exercise to
incident the moment the host is not yours.
