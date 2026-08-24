#!/usr/bin/env python3
"""Phoenix-style exploitation ladder over a plain TCP service.

Five stages, each printing its own memory map and grading one payload
before the next rung opens. The ladder validates hand-built byte
strings against the printed maps; no memory corruption happens and
nothing is executed. Payloads are raw bytes terminated by newline.
"""

import os
import re
import secrets
import socket
import struct
import threading

PORT = 4000
FLAG = os.environ.get("ROOM_FLAG", "FLAGNOTSET0000000000000000")

BUFFER_SIZE = 64
WIN_1 = 0x004012A3
WIN_2 = 0x00401307
MAGIC = 0xC0FFEE1234567890
SLOT_SECRET = 5
SLOT_WRITE = 6
WRITE_TARGET = 1337
POP_RDI = 0x0040124C
BINSH_STR = 0x00402004
SYSTEM_PLT = 0x00401060


def p64(value: int) -> bytes:
    return struct.pack("<Q", value)


def _random_slot() -> int:
    value = int.from_bytes(secrets.token_bytes(7) + b"\x00", "little")
    while value == MAGIC:
        value = int.from_bytes(secrets.token_bytes(7) + b"\x00", "little")
    return value


class Ladder:
    """One climber's session state."""

    def __init__(self) -> None:
        canary_int = int.from_bytes(secrets.token_bytes(8), "little")
        while b"\n" in p64(canary_int):
            canary_int = int.from_bytes(secrets.token_bytes(8), "little")
        self.canary = canary_int
        slots = [_random_slot() for _ in range(10)]
        slots[SLOT_SECRET] = MAGIC
        self.slots = slots

    def map_stage1(self) -> str:
        return (
            "STAGE 1 of 5: stack overflow, ret2win\n"
            f"map: BUFFER_SIZE={BUFFER_SIZE} (bytes)\n"
            f"map: saved return @ offset {BUFFER_SIZE}\n"
            f"map: win() = {hex(WIN_1)}\n"
            "task: overwrite the saved return with win().\n"
        )

    def check_stage1(self, data: bytes) -> str | None:
        if len(data) != BUFFER_SIZE + 8:
            return f"FAIL stage 1: expected {BUFFER_SIZE + 8} bytes, got {len(data)}"
        if data[:BUFFER_SIZE] != b"A" * BUFFER_SIZE:
            return "FAIL stage 1: first 64 bytes must be filler ('A')"
        if data[BUFFER_SIZE:] != p64(WIN_1):
            return f"FAIL stage 1: last 8 bytes must be little-endian {hex(WIN_1)}"
        return "STAGE 1 PASS (1/5): return address redirected to win()\n"

    def map_stage2(self) -> str:
        return (
            "STAGE 2 of 5: stack canary carried intact\n"
            "map: buffer   @ rsp+0 .. rsp+63\n"
            f"map: canary   @ rsp+64 value {hex(self.canary)}\n"
            "map: saved rbp @ rsp+72 (any 8 filler bytes)\n"
            "map: saved return @ rsp+80\n"
            f"map: win() = {hex(WIN_2)}\n"
            "task: keep the canary byte-exact, replace only the return.\n"
        )

    def check_stage2(self, data: bytes) -> str | None:
        if len(data) != 88:
            return f"FAIL stage 2: expected 88 bytes, got {len(data)}"
        if data[:64] != b"A" * 64:
            return "FAIL stage 2: buffer must be 64 filler bytes"
        if data[64:72] != p64(self.canary):
            return "FAIL stage 2: canary must survive byte-exact from the map"
        if data[80:] != p64(WIN_2):
            return f"FAIL stage 2: return @ rsp+80 must be little-endian {hex(WIN_2)}"
        return "STAGE 2 PASS (2/5): canary intact, return hijacked\n"

    def map_stage3(self) -> str:
        dump = "\n".join(f"map: slot {i} : {hex(v)}" for i, v in enumerate(self.slots))
        return (
            "STAGE 3 of 5: format string read\n"
            f"brief: one slot holds the magic word {hex(MAGIC)}\n"
            f"{dump}\n"
            "engine: %<slot>$p expands to that slot's hex value.\n"
            "task: leak the magic word, then echo it back as 0x...\n"
        )

    def run_stage3(self, recv_line) -> str | None:  # type: ignore[no-untyped-def]
        spec = recv_line("payload> ").decode(errors="replace").strip()
        match = re.fullmatch(r"%(\d+)\$p", spec)
        if not match:
            return "FAIL stage 3: send exactly %<slot>$p"
        slot = int(match.group(1))
        if not 0 <= slot < len(self.slots):
            return "FAIL stage 3: slot out of range"
        leaked = self.slots[slot]
        answer = recv_line(f"LEAK: {hex(leaked)}\necho> ").decode(errors="replace").strip().lower()
        if answer != hex(MAGIC):
            return "FAIL stage 3: echoed value does not match the magic word"
        if slot != SLOT_SECRET:
            return "FAIL stage 3: right value, wrong route; leak via its own slot"
        return "STAGE 3 PASS (3/5): secret read through positional specifier\n"

    def map_stage4(self) -> str:
        return (
            "STAGE 4 of 5: format string write\n"
            f"map: write slot = {SLOT_WRITE}\n"
            f"map: required value = {WRITE_TARGET}\n"
            "engine: literal characters before %<slot>$n are counted;\n"
            "engine: the count is written into that slot as an integer.\n"
            "task: make slot 6 equal 1337 using padding plus %6$n.\n"
        )

    def check_stage4(self, data: bytes) -> str | None:
        text = data.decode(errors="replace")
        match = re.search(r"(%(\d+)\$n)$", text)
        if not match:
            return "FAIL stage 4: payload must end with %<slot>$n"
        slot = int(match.group(2))
        literal_count = len(text[: match.start(1)])
        if slot != SLOT_WRITE:
            return f"FAIL stage 4: wrong slot; the map names slot {SLOT_WRITE}"
        if literal_count != WRITE_TARGET:
            return f"FAIL stage 4: wrote {literal_count}, the target is {WRITE_TARGET}"
        return f"STAGE 4 PASS (4/5): slot {slot} now holds {literal_count}\n"

    def map_stage5(self) -> str:
        return (
            "STAGE 5 of 5: ret2libc call chain\n"
            f"map: pop rdi ; ret gadget = {hex(POP_RDI)}\n"
            f"map: /bin/sh string      = {hex(BINSH_STR)}\n"
            f"map: system plt          = {hex(SYSTEM_PLT)}\n"
            "task: chain them so system receives /bin/sh in rdi:\n"
            "task: [pop_rdi][binsh][system], each little-endian 8 bytes.\n"
        )

    def check_stage5(self, data: bytes) -> str | None:
        if len(data) != 24:
            return f"FAIL stage 5: expected 24 bytes, got {len(data)}"
        want = p64(POP_RDI) + p64(BINSH_STR) + p64(SYSTEM_PLT)
        if data != want:
            return "FAIL stage 5: chain order or values wrong; see the map"
        return f"STAGE 5 PASS (5/5): chain assembled, simulated shell reached\n\n{FLAG}\n"


BANNER = (
    "=== Phoenix Stack training ladder ===\n"
    "Five rungs, one connection. Each rung prints its memory map,\n"
    "then grades your raw-byte payload (terminate with \\n).\n"
    "Nothing here executes: the grader compares bytes against maps.\n"
)


def handle(conn: socket.socket) -> None:
    try:
        conn.sendall(BANNER.encode())
        ladder = Ladder()

        def recv_line(prompt: str) -> bytes:
            conn.sendall(prompt.encode())
            buf = bytearray()
            while True:
                chunk = conn.recv(4096)
                if not chunk:
                    raise OSError("peer closed")
                buf += chunk
                if b"\n" in buf:
                    line, _, _rest = buf.partition(b"\n")
                    return line.rstrip(b"\r")

        def grade(verdict: str | None) -> bool:
            text = verdict or "FAIL internal error"
            conn.sendall((text + "\n").encode())
            return not text.startswith("FAIL")

        conn.sendall(ladder.map_stage1().encode())
        if not grade(ladder.check_stage1(recv_line("payload> "))):
            return
        conn.sendall(ladder.map_stage2().encode())
        if not grade(ladder.check_stage2(recv_line("payload> "))):
            return
        conn.sendall(ladder.map_stage3().encode())
        if not grade(ladder.run_stage3(recv_line)):
            return
        conn.sendall(ladder.map_stage4().encode())
        if not grade(ladder.check_stage4(recv_line("payload> "))):
            return
        conn.sendall(ladder.map_stage5().encode())
        grade(ladder.check_stage5(recv_line("payload> ")))
    except OSError:
        pass
    finally:
        try:
            conn.close()
        except OSError:
            pass


def main() -> None:
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("0.0.0.0", PORT))
    srv.listen(16)
    while True:
        conn, _addr = srv.accept()
        threading.Thread(target=handle, args=(conn,), daemon=True).start()


if __name__ == "__main__":
    main()
