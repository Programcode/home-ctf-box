# Dockerlabs Vibes

Community vulnerable-machine platforms love container misconfiguration
rooms because the lesson transfers directly to cloud infrastructure:
on any host where the container daemon listens on a unix socket, the
group that owns that socket owns the machine. Anyone in the docker
group can ask the privileged daemon to bind-mount the host root
filesystem into a container and read it back, which makes membership
a quieter but equally total form of passwordless root. Auditors find
this exact issue on production systems every week, usually because
some service account was added to the group years ago and nobody
remembered why.

## What you will practice

This room simulates that arrangement honestly, and it says so up
front: there is no real Docker daemon or socket anywhere in the
image. A small helper called dockersim plays the daemon's role with a
deliberately tiny documented surface, and a sudo grant limited to the
docker group plays the role of socket ownership. What survives the
simulation is the reasoning you would use on a real engagement.

First, privilege inventory as a habit. The first command worth typing
on any shell is id, because group membership is where hosts hide
their most generous grants. Finding your account in the docker group
should immediately change your mental model of what this box will
let you do.

Second, reading interfaces before swinging at them. The helper
documents itself twice over, through help output and an API manual,
and both make the supported subset explicit: two allowlisted images,
exactly one mount with src and dst, one command. Real tooling works
the same way; the operators who get value from a new interface are
the ones who learn its grammar first. You will also discover where
ops records its host-sync paths by reading the ps listing's labels,
which rewards attention to structured output.

Third, confirming the boundary before crossing it. Before using the
privileged path you will attempt the direct route and watch it fail
with permission denied. That negative result is part of the lesson:
the whole point of the misconfiguration class is that ordinary access
control stays intact while the daemon route bypasses it. Your final
command asks the privileged helper to mount the protected file and
cat it from inside the simulated container, and the flag it prints is
proof you drove the documented interface rather than fought it.

## Scope

Only SSH on port 22 of your own lab instance is in scope. The only
privileged code in the image is the dockersim helper itself,
reachable solely through a sudo grant for docker group members, and
its run action performs exactly one file read inside the same
disposable container. No namespaces are created, no real mounts
occur, nothing touches the host, and no container runtime exists
anywhere in the build. The safety notes in this room's manifest say
the same thing plainly because honest disclosure is part of the
lesson: when you simulate a dangerous misconfiguration, you owe the
learner an accurate account of where the simulation ends.

Stay inside the documented subset as you work, even though you will
quickly see how the helper could be abused if its guards were
weaker. The image allowlist, the /hostsim boundary, and the cat-only
command rule exist so the exercise stays a teaching exercise.
Treat the group membership finding as the takeaway that matters on
real infrastructure: if you find yourself in the docker group on a
production host, you hold root there, and any audit that misses this
check is incomplete. Flag it, explain the daemon-mediated path to
root in one paragraph, and move on; that report line alone justifies
the habits this room drills.
