"""Intended-path solver: threshold demodulation, run-length bits, replay the static word."""

import struct
from collections import Counter

import httpx

from openrange.content.solver import SolveResult, TaskResult, find_flags

THRESHOLD = 3000


def decode_static(iq: bytes) -> tuple[int, list[int]]:
    vals = struct.unpack(f"<{len(iq) // 2}h", iq)
    ichannel = vals[0::2]
    levels = [1 if abs(sample) > THRESHOLD else 0 for sample in ichannel]

    runs: list[tuple[int, int]] = []
    current, count = levels[0], 0
    for level in levels:
        if level == current:
            count += 1
        else:
            runs.append((current, count))
            current, count = level, 1
    runs.append((current, count))

    bits = ""
    for level, length in runs:
        assert length % 8 == 0, f"ragged run {level}x{length}"
        bits += str(level) * (length // 8)

    candidates = []
    cursor = 0
    while True:
        cursor = bits.find("10101010", cursor)
        if cursor == -1:
            break
        frame = bits[cursor + 8 : cursor + 72]
        if len(frame) == 64:
            candidates.append((int(frame[:32], 2), int(frame[32:], 2)))
        cursor += 8

    counts = Counter(static for static, _ in candidates)
    best = counts.most_common(2)
    assert len(best) >= 1 and (len(best) == 1 or best[0][1] > best[1][1]), f"ambiguous {best}"
    static_code = best[0][0]
    assert best[0][1] >= 2, f"static word seen only once: {best}"

    rolls = [roll for static, roll in candidates if static == static_code]
    assert all(b > a for a, b in zip(rolls, rolls[1:])), rolls
    return static_code, rolls


def solve(ctx) -> SolveResult:  # type: ignore[no-untyped-def]
    expected = ctx.expected_flags["decode-and-open"]
    client = httpx.Client(base_url=ctx.url(), timeout=10)
    png_head = client.get("/evidence/spectrum.png").content[:8]
    assert png_head.startswith(b"\x89PNG"), "spectrum plot should be a PNG"

    iq = client.get("/evidence/capture.iq").content
    static_code, _rolls = decode_static(iq)

    resp = client.get("/garage/open", params={"code": f"{static_code:08X}"})
    client.close()
    flags = find_flags(resp.text)
    captured = flags[0] if flags else None
    ok = captured == expected
    detail = None if ok else f"static={static_code:08X} status={resp.status_code}"
    return SolveResult(
        results=[TaskResult(task_id="decode-and-open", ok=ok, captured=captured, detail=detail)]
    )
