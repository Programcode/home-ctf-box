"""Intended-path solver: read /metrics, route to the tunnel subnet."""

import re

import httpx

from openrange.content.solver import SolveResult, TaskResult, find_flags

ROUTE_LINE = re.compile(r'routesim_route\{dev="([^"]+)",dest="([^"]+)"\}')


def solve(ctx) -> SolveResult:  # type: ignore[no-untyped-def]
    base = ctx.url()
    metrics = httpx.get(f"{base}/metrics", timeout=10).text
    pairs = ROUTE_LINE.findall(metrics)
    if not pairs:
        return SolveResult(
            results=[
                TaskResult(
                    task_id="steer-to-remote-segment",
                    ok=False,
                    detail="no routesim_route entries found in /metrics",
                )
            ]
        )

    # Enumerate deliberately: the tunnel-style interface first, then the rest.
    tunnel_first = [dest for dev, dest in pairs if dev.startswith("tun")]
    tunnel_first += [dest for dev, dest in pairs if not dev.startswith("tun")]

    captured = None
    tried: list[str] = []
    for dest in dict.fromkeys(tunnel_first):
        res = httpx.post(f"{base}/route", json={"subnet": dest}, timeout=10)
        tried.append(dest)
        flags = find_flags(res.text)
        if flags:
            captured = flags[0]
            break

    return SolveResult(
        results=[
            TaskResult(
                task_id="steer-to-remote-segment",
                ok=bool(captured),
                captured=captured,
                detail=None if captured else f"no flag from routing {', '.join(tried)}",
            )
        ]
    )
