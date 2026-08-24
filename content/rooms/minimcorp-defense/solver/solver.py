"""Intended-path solver: derive every answer from the evidence exports, close the case."""

import re

import httpx
from openrange.content.solver import SolveResult, TaskResult, find_flags

TASK_ID = "close-the-case"


def solve(ctx) -> SolveResult:  # type: ignore[no-untyped-def]
    base = ctx.url()
    detail = None
    captured = None

    edge_text = httpx.get(base + "/evidence/edge-access.log", timeout=10).text
    wiki = httpx.get(base + "/evidence/wiki-audit.json", timeout=10).json()
    finance = httpx.get(base + "/evidence/finance-access.json", timeout=10).json()
    sso = httpx.get(base + "/evidence/directory-sso.json", timeout=10).json()

    m_edge = re.search(r"(\d{2}:\d{2}):\d{2}Z GET /static/vpn\.conf\.bak", edge_text)
    t_config = m_edge.group(1) if m_edge else ""
    wiki_auths = [
        e for e in wiki["events"] if e["kind"] == "auth" and str(e["src"]).startswith("198.51.")
    ]
    t_reuse = str(wiki_auths[0]["time"])[:5] if wiki_auths else ""
    inv_reads = sorted(finance["events"], key=lambda e: e["time"])
    t_enum = min(str(e["time"])[:5] for e in inv_reads) if inv_reads else ""
    sso_issues = [
        e for e in sso["events"] if e["kind"] == "sso-verify" and e.get("outcome") == "token-issued"
    ]
    t_forge = str(sso_issues[0]["time"])[:5] if sso_issues else ""

    steps = [
        {"time": t_config, "event": "config-exposure"},
        {"time": t_reuse, "event": "credential-reuse"},
        {"time": t_enum, "event": "data-enumeration"},
        {"time": t_forge, "event": "privilege-forgery"},
    ]
    timeline = httpx.post(base + "/timeline", json={"steps": steps}, timeout=10)
    if timeline.status_code != 200 and detail is None:
        detail = f"timeline rejected: {timeline.json()}"

    affected: set[str] = set()
    for event in wiki_auths:
        affected.add(str(event["user"]))
    for event in inv_reads:
        affected.add(str(event["record"]))
    for event in sso_issues:
        affected.add(str(event["user"]))
    accounts = httpx.post(base + "/accounts", json={"affected": sorted(affected)}, timeout=10)
    if accounts.status_code != 200 and detail is None:
        detail = f"accounts rejected: {accounts.json()}"

    options = httpx.get(base + "/playbook", timeout=10).json()["containment_options"]
    root_causes = {
        "purge-stale-vpn-backups",
        "rotate-wiki-service-credentials",
        "revoke-fin-api-key",
        "retire-legacy-sso-signing",
        "add-per-record-authorization",
    }
    valid_slugs = {o["slug"] for o in options}
    actions = sorted(root_causes & valid_slugs)
    if len(actions) != 5 and detail is None:
        detail = f"playbook offered fewer root-cause actions than expected: {sorted(valid_slugs)}"
    contain = httpx.post(base + "/contain", json={"actions": actions}, timeout=10)
    if contain.status_code != 200 and detail is None:
        detail = f"contain rejected: {contain.json()}"

    closed = httpx.post(base + "/close-case", json={}, timeout=10).json()
    flags = find_flags(closed.get("flag") or "")
    if closed.get("closed") and flags:
        captured = flags[0]
    elif detail is None:
        detail = f"case not closed: {closed}"

    return SolveResult(
        results=[
            TaskResult(task_id=TASK_ID, ok=captured is not None, captured=captured, detail=detail)
        ]
    )
