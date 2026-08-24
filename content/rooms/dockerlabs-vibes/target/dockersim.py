#!/usr/bin/env python3
"""dockersim: a documented, minimal container-daemon simulator.

There is no real Docker here. This helper exists to teach why docker
group membership is root-equivalent: its privileged run action reads
a host file through a simulated bind mount, exactly like a real
daemon would when asked. The supported surface is only what API.md
documents; everything else is refused.
"""

import os
import sys

ALLOWED_IMAGES = {"alpine", "debian"}
HOSTSIM_ROOT = "/hostsim"

MANUAL = """dockersim 1.0, documented subset:

  dockersim help                       this manual
  dockersim info                       daemon-sim status and policy
  dockersim ps                         simulated containers + labels
  dockersim run --image NAME --mount src=P,dst=P -- cat FILE

images: alpine, debian; one mount; command limited to cat.
See /usr/share/doc/dockersim/API.md for the full manual."""

PS_TABLE = """CONTAINER ID   IMAGE     STATUS    LABELS
9f2c1a4b7d55   webapp    Up 3 d    ROLE=frontend
e5110c8a93f7   vaultbox  Exited    ROLE=sync-vault HOSTSYNC=/hostsim/root"""


def die(message: str) -> None:
    print(f"dockersim: {message}")
    raise SystemExit(1)


def require_root() -> None:
    if os.getuid() != 0:
        die(
            "cannot reach the simulated daemon socket: permission denied "
            "(the daemon-sim answers only the documented access path)"
        )


def cmd_info() -> None:
    print("daemon-sim: running (simulation)")
    print("socket: /var/run/dockersim.sock (virtual)")
    print("policy: requests accepted only via the documented sudo grant")
    print("reality check: no real daemon, socket, or containers exist")


def cmd_ps() -> None:
    print(PS_TABLE)


def parse_run(argv: list[str]) -> tuple[str, str, str]:
    image = None
    mount = None
    rest: list[str] = []
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--image":
            image = argv[i + 1] if i + 1 < len(argv) else None
            i += 2
        elif arg == "--mount":
            mount = argv[i + 1] if i + 1 < len(argv) else None
            i += 2
        elif arg == "--":
            rest = argv[i + 1 :]
            break
        else:
            die(f"unsupported flag {arg!r}; see 'dockersim help'")
    if not image or not mount or not rest:
        die("run needs --image, --mount src=...,dst=... and '-- cat FILE'")
    if image not in ALLOWED_IMAGES:
        die(f"image {image!r} is not in the allowlist {sorted(ALLOWED_IMAGES)}")

    src = dst = None
    for part in mount.split(","):
        key, sep, value = part.partition("=")
        if sep and key.strip() == "src":
            src = value.strip()
        elif sep and key.strip() == "dst":
            dst = value.strip()
    if not src or not dst:
        die("mount must look like src=/host/path,dst=/container/path")
    if not dst.startswith("/"):
        die("dst must be an absolute path inside the simulated container")
    return src, dst, " ".join(rest)


def cmd_run(argv: list[str]) -> None:
    require_root()
    src, dst, command = parse_run(argv)
    real = os.path.realpath(src)
    if not (real.startswith(HOSTSIM_ROOT + os.sep) or real == HOSTSIM_ROOT):
        die("src must live under /hostsim per the documented subset")
    if not os.path.isfile(real):
        die(f"src {src} is not an existing regular file")

    parts = command.split()
    if len(parts) != 2 or parts[0] != "cat" or parts[1] != dst:
        die("the only supported command is 'cat <mounted dst>'")

    print(f"[vaultbox-sim alpine] mounting {src} -> {dst}")
    try:
        with open(real, encoding="utf-8") as fh:
            content = fh.read()
    except OSError as exc:
        die(f"daemon-sim could not read the mounted source: {exc}")
    print(f"[vaultbox-sim alpine]$ cat {dst}")
    print(content.rstrip())
    print("[vaultbox-sim alpine] exit 0")


def main() -> None:
    args = sys.argv[1:]
    if not args or args[0] in ("help", "--help", "-h"):
        print(MANUAL)
        return
    verb = args[0]
    if verb == "info":
        cmd_info()
    elif verb == "ps":
        cmd_ps()
    elif verb == "run":
        cmd_run(args[1:])
    else:
        die(f"unknown command {verb!r}; see 'dockersim help'")


if __name__ == "__main__":
    main()
