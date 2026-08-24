"""Intended-path solver: hypothesis-driven hunt across auth, proxy, and dns evidence."""

from collections import defaultdict
from datetime import datetime
from itertools import pairwise

import httpx

from openrange.content.solver import SolveResult, TaskResult


def _ts(line: str) -> datetime:
    return datetime.strptime(line[:19], "%Y-%m-%dT%H:%M:%S")


def _from_client(line: str, ip: str) -> bool:
    parts = line.split("client=", 1)
    return len(parts) == 2 and parts[1].startswith(ip + " ")


def solve(ctx) -> SolveResult:  # type: ignore[no-untyped-def]
    expected = ctx.expected_flags["hunt-the-beacon"]
    with httpx.Client(base_url=ctx.url(), timeout=10) as client:
        auth = client.get("/evidence/auth.log").text.splitlines()
        proxy = client.get("/evidence/proxy.log").text.splitlines()
        dns = client.get("/evidence/dns.log").text.splitlines()

        # Stage 1: service account with a failure burst (>=5) then a
        # success from an address outside the internal 10.x range.
        failures = defaultdict(int)
        for line in auth:
            if "result=failure" in line:
                user = line.split("user=", 1)[1].split(" ", 1)[0]
                failures[user] += 1
        candidates = [
            line
            for line in auth
            if "result=success" in line
            and failures.get(line.split("user=", 1)[1].split(" ", 1)[0], 0) >= 5
            and not line.split("src=", 1)[1].startswith("10.")
        ]
        assert len(candidates) == 1, f"stage 1 ambiguous: {candidates}"
        compromised_user = candidates[0].split("user=", 1)[1].split(" ", 1)[0]

        # Stage 2: external source of that success.
        success_line = candidates[0]
        source_ip = success_line.split("src=", 1)[1].split(" ", 1)[0]
        assert not source_ip.startswith("10."), "success came from an internal address"

        # Victim workstation comes from the assign event naming the user.
        assign_lines = [
            line for line in auth if "event=assign" in line and compromised_user in line
        ]
        assert len(assign_lines) == 1, "expected exactly one vpn assignment"
        victim_ip = assign_lines[0].split("ip=", 1)[1].split(" ", 1)[0]

        # Stage 3: oversized upload from the victim names the staging host.
        uploads = [line for line in proxy if _from_client(line, victim_ip) and " POST " in line]
        big_upload = [
            line for line in uploads if int(line.rsplit("bytes=", 1)[1].split(" ", 1)[0]) > 40000
        ]
        assert len(big_upload) == 1, f"stage 3 ambiguous: {big_upload}"
        staging_host = big_upload[0].split("http://", 1)[1].split("/", 1)[0]

        # Stage 4: long-label TXT queries under one parent domain.
        parents = set()
        for line in dns:
            if not _from_client(line, victim_ip):
                continue
            qname = line.split("qname=", 1)[1].split(" ", 1)[0]
            labels = qname.split(".")
            if len(labels) >= 3 and max(len(label) for label in labels[:-2]) >= 30:
                parents.add(".".join(labels[-2:]))
        assert len(parents) == 1, f"stage 4 ambiguous: {parents}"
        tunnel_domain = parents.pop()

        # Stage 5: metronome beaconing from the victim in the proxy log.
        per_host = defaultdict(list)
        for line in proxy:
            if not _from_client(line, victim_ip):
                continue
            host = line.split("http://", 1)[1].split("/", 1)[0]
            per_host[host].append(_ts(line))
        beacons = {}
        for host, times in per_host.items():
            times.sort()
            gaps = {(b - a).total_seconds() for a, b in pairwise(times)}
            if len(times) >= 3 and gaps == {300.0}:
                beacons[host] = len(times)
        assert list(beacons) == ["cdn-metrics-sync.top"], f"stage 5 ambiguous: {beacons}"
        c2_domain = next(iter(beacons))

        answers = [compromised_user, source_ip, staging_host, tunnel_domain, c2_domain]

        captured = None
        for index, answer in enumerate(answers, start=1):
            question = client.get("/hunt").json()
            assert question["stage"] == index, f"hunt state drifted at {index}"
            verdict = client.post("/hunt", json={"answer": answer}).json()
            assert verdict["status"] != "incorrect", f"wrong answer {answer!r}: {verdict}"
            if verdict["status"] == "complete":
                captured = verdict["flag"]

    ok = captured == expected
    detail = None if ok else f"answers={answers}"
    return SolveResult(
        results=[TaskResult(task_id="hunt-the-beacon", ok=ok, captured=captured, detail=detail)]
    )
