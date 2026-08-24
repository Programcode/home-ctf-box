dockersim 1.0, documented API subset
====================================

This helper stands in for a container daemon on hosts where the real
thing is unavailable. It is intentionally tiny and intentionally
documented: everything it can do appears below, and anything not
listed here is unsupported.

Commands

dockersim help
Print this manual.

dockersim info
Show daemon-sim status and the access policy.

dockersim ps
List simulated containers and their labels. Labels are part of
the documented output; ops uses them to record host-sync paths.

dockersim run --image NAME --mount src=PATH,dst=PATH -- cat FILE
Simulate running one allowlisted image with exactly one bind
mount, then execute the only supported command (cat) against
the mounted file inside the simulated container. The daemon-sim
reads the source path with its own privileges, which is why a
mount of a protected file behaves like it does on a host where
the docker group can ask the daemon to read anything.

Constraints

- images: alpine, debian
- mounts: exactly one; src must be an existing regular file under
  /hostsim; dst must be an absolute path inside the container
- commands: cat FILE where FILE is the dst you mounted
- everything else answers with an unsupported message

Access policy

The daemon-sim accepts requests only through the documented sudo
grant for members of the docker group. This mirrors the standing
reality on container hosts: membership in that group is equivalent
to root, because the daemon runs privileged and will happily bind
mount host files into containers on request.
