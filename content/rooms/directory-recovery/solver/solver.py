"""Intended-path solver: derive the recovery plan from the evidence pack."""

import re

import httpx

from openrange.content.solver import SolveResult, TaskResult, find_flags

PLAN = [
    "isolate-network",
    "preserve-forensics",
    "rebuild-dc-from-clean-media",
    "restore-selected-backup",
    "reset-compromised-credentials",
    "verify-services-and-monitor",
]


def solve(ctx) -> SolveResult:  # type: ignore[no-untyped-def]
    base = ctx.url()
    detail = None

    note = httpx.get(f"{base}/evidence/ransom-note.txt", timeout=10).text
    times = re.findall(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", note)
    t0 = min(times) if times else None
    if not t0:
        return SolveResult(
            results=[TaskResult("recover-domain", False, None, "no timestamp in ransom note")]
        )

    accounts: list[dict] = []
    for part in ("part1", "part2"):
        doc = httpx.get(f"{base}/evidence/ntds-sim-dump-{part}.json", timeout=10).json()
        accounts.extend(doc["accounts"])
    rogue = sorted(
        a["sAMAccountName"] for a in accounts if a["whenCreated"] >= t0 or a["whenChanged"] >= t0
    )
    if not rogue and detail is None:
        detail = f"no post-compromise directory changes found after {t0}"

    backups = httpx.get(f"{base}/evidence/backups-inventory.json", timeout=10).json()["backups"]
    usable = [b for b in backups if b["taken"] < t0 and b["verified_offline"]]
    restore_source = usable[0]["id"] if len(usable) == 1 else None
    if not restore_source and detail is None:
        detail = (
            f"expected exactly one clean pre-compromise backup, saw {[b['id'] for b in usable]}"
        )

    menu = httpx.get(f"{base}/recover/menu", timeout=10).json()["steps"]
    unknown = [step for step in PLAN if step not in menu]
    if unknown and detail is None:
        detail = f"plan steps absent from menu: {unknown}"

    reply = httpx.post(
        f"{base}/recover",
        json={"rogue_accounts": rogue, "restore_source": restore_source, "sequence": PLAN},
        timeout=10,
    ).json()
    captured = None
    flags = find_flags(reply.get("flag") or "")
    if reply.get("status") == "restored" and flags:
        captured = flags[0]
    elif detail is None:
        detail = f"recovery not verified: {reply}"

    return SolveResult(
        results=[
            TaskResult(
                task_id="recover-domain",
                ok=captured is not None,
                captured=captured,
                detail=detail,
            )
        ]
    )
