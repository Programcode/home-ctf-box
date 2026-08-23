"""Solve every room bundle; used by `make test-solvers` and CI."""

from __future__ import annotations

import sys
from pathlib import Path

from openrange.content.harness import solve_room


def main(argv: list[str]) -> int:
    roots = [Path(a) for a in argv] or [Path("content/rooms")]
    rooms: list[Path] = []
    for root in roots:
        if (root / "room.yaml").exists():
            rooms.append(root)
        else:
            rooms.extend(p for p in sorted(root.glob("*")) if (p / "room.yaml").exists())
    rooms = sorted(set(rooms))
    if not rooms:
        print("no room bundles found", file=sys.stderr)
        return 2
    failures: list[str] = []
    for room in rooms:
        result = solve_room(room)
        mark = "PASS" if result.solved else "FAIL"
        print(f"[{mark}] {result.slug}: {result.detail}")
        if not result.solved:
            failures.append(result.slug)
    print(f"\n{len(rooms) - len(failures)}/{len(rooms)} rooms passed the solver gate")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
