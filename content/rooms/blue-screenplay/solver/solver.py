"""Intended-path solver: parse the evtx-sim exports, answer, file the report."""

import httpx

from openrange.content.solver import SolveResult, TaskResult, find_flags


def _is_external(ip: str) -> bool:
    return not (ip.startswith("10.") or ip.startswith("192.168.") or ip.startswith("172."))


def solve(ctx) -> SolveResult:  # type: ignore[no-untyped-def]
    base = ctx.url()
    security = httpx.get(f"{base}/evidence/security.evtx-sim.json", timeout=10).json()
    system = httpx.get(f"{base}/evidence/system.evtx-sim.json", timeout=10).json()

    failures = [e for e in security if e["event_id"] == "4625-sim" and _is_external(e["source_ip"])]
    bursts: dict[str, int] = {}
    for event in failures:
        bursts[event["source_ip"]] = bursts.get(event["source_ip"], 0) + 1
    attacker_ip = max(bursts, key=lambda ip: bursts[ip]) if bursts else None
    detail = None
    if not attacker_ip:
        detail = "no external failure burst found"

    targeted = {e["account"] for e in failures if e["source_ip"] == attacker_ip}
    compromised_account = None
    for event in sorted(
        (e for e in security if e["event_id"] == "4624-sim" and e.get("result") == "success"),
        key=lambda e: e["time"],
    ):
        if event["source_ip"] == attacker_ip and event["account"] in targeted:
            compromised_account = event["account"]
            break
    if not compromised_account and detail is None:
        detail = "no successful logon followed the burst"

    hops = [
        e
        for e in security
        if e["event_id"] == "4624-sim"
        and e.get("result") == "success"
        and e["account"] == compromised_account
        and not _is_external(e["source_ip"])
    ]
    hosts_by_source: dict[str, set[str]] = {}
    for event in hops:
        hosts_by_source.setdefault(event["source_ip"], set()).add(event["host"])
    movers = [ip for ip, hosts in hosts_by_source.items() if len(hosts) >= 2]
    lateral_source_ip = movers[0] if len(movers) == 1 else None
    if not lateral_source_ip and detail is None:
        detail = f"expected one internal pivot source, saw {sorted(hosts_by_source)}"

    crashes = sorted((e for e in system if e["event_id"] == "7031-sim"), key=lambda e: e["time"])
    first_failed_service = crashes[0]["service"] if crashes else None
    if not first_failed_service and detail is None:
        detail = "no service crashes in System channel"

    answers = {
        "compromised_account": compromised_account,
        "first_failed_service": first_failed_service,
        "lateral_source_ip": lateral_source_ip,
    }
    reply = httpx.post(
        f"{base}/report",
        json={"answers": answers},
        timeout=10,
    ).json()
    captured = None
    flags = find_flags(reply.get("flag") or "")
    if reply.get("status") == "verified" and flags:
        captured = flags[0]
    elif detail is None:
        detail = f"report incomplete with derived answers {answers}: {reply}"

    return SolveResult(
        results=[
            TaskResult(
                task_id="incident-report",
                ok=captured is not None,
                captured=captured,
                detail=detail,
            )
        ]
    )
