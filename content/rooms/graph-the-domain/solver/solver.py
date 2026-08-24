"""Intended-path solver: derive every quiz answer from the collected graph."""

from collections import deque

import httpx

from openrange.content.solver import SolveResult, TaskResult, find_flags

START = "dana.reyes"
TARGET = "DOMAIN ADMINS"


def _shortest_hops(graph: dict, src: str, dst: str) -> int:
    """Undirected hop count over the edge list."""
    adjacency: dict[str, list[str]] = {}
    for edge in graph["edges"]:
        adjacency.setdefault(edge["src"], []).append(edge["dst"])
        adjacency.setdefault(edge["dst"], []).append(edge["src"])
    seen = {src}
    queue = deque([(src, 0)])
    while queue:
        node, depth = queue.popleft()
        if node == dst:
            return depth
        for neighbor in adjacency.get(node, []):
            if neighbor not in seen:
                seen.add(neighbor)
                queue.append((neighbor, depth + 1))
    return -1


def _answers(graph: dict) -> dict[str, str]:
    edges = graph["edges"]
    da_members = [e["src"] for e in edges if e["rel"] == "MemberOf" and e["dst"] == TARGET]
    resetters = [
        e["src"] for e in edges if e["rel"] == "CanResetPassword" and e["dst"] == "svc_backup"
    ]
    sessions = [e["dst"] for e in edges if e["rel"] == "HasSession" and e["src"] == "svc_backup"]
    file01_admins = [e["src"] for e in edges if e["rel"] == "AdminOn" and e["dst"] == "FILE-01"]
    return {
        "q1": str(_shortest_hops(graph, START, TARGET)),
        "q2": da_members[0] if da_members else "",
        "q3": str(len(resetters)),
        "q4": sessions[0] if sessions else "",
        "q5": file01_admins[0] if file01_admins else "",
    }


def solve(ctx) -> SolveResult:  # type: ignore[no-untyped-def]
    base = ctx.url("target")
    res = httpx.get(f"{base}/collect/graph.json", timeout=10)
    graph = res.json()

    answers = _answers(graph)
    if len(set(answers.values())) != 5 or "" in answers.values():
        return SolveResult(
            results=[
                TaskResult(
                    task_id="map-and-quiz",
                    ok=False,
                    detail=f"graph derivation incomplete: {answers}",
                )
            ]
        )

    res = httpx.post(f"{base}/quiz", data=answers, timeout=10)
    flags = find_flags(res.text)
    captured = flags[0] if flags else None
    detail = None
    if not captured:
        detail = f"quiz rejected derived answers {answers}: {res.text[:200]}"
    return SolveResult(
        results=[
            TaskResult(task_id="map-and-quiz", ok=bool(captured), captured=captured, detail=detail)
        ]
    )
