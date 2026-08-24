#!/usr/bin/env python3
"""responder-sim: simulated LLMNR/NBT-NS responder for the name-resolution room.

This is a teaching simulation, not a security tool. It listens on two
loopback UDP ports as stand-ins for LLMNR (5355) and NBT-NS (137), logs
every name query it sees, and answers exactly one configured name with a
clearly labeled fake credential blob. Nothing here speaks the real
LLMNR, NBT-NS, or NTLM wire formats, and nothing here touches real
credentials.
"""

import hashlib
import hmac
import os
import socket
import threading
import time

POISON_NAME = "FILESRV01"
SEED = b"openrange-name-resolution-sim-v1"
QUERY_LOG = "/var/log/responder-sim/queries.log"
CAPTURE_LOG = "/srv/public/responder-capture.log"
SERVICES = (("llmnr", 5355), ("nbtns", 137))


def sim_blob(name: str) -> str:
    digest = hmac.new(SEED, name.upper().encode(), hashlib.sha256).hexdigest()[:32]
    return f"SIM-HASH-{digest}"


def log(path: str, line: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(time.strftime("%FT%T ") + line + "\n")


def serve(proto: str, port: int) -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("127.0.0.1", port))
    print(f"[simulation] responder-sim {proto} listening on 127.0.0.1:{port}", flush=True)
    while True:
        try:
            data, addr = sock.recvfrom(2048)
        except OSError:
            continue
        parts = data.decode(errors="replace").strip().split("|")
        if len(parts) != 3 or parts[0] != "QRY":
            continue
        _, _proto_tag, name = parts[0], parts[1], parts[2].strip()
        log(QUERY_LOG, f"{proto} query for '{name}' from 127.0.0.1:{addr[1]}")
        if name.upper() != POISON_NAME:
            continue
        # The poisoning moment, simulated: this responder claims the name
        # and records a fake authentication blob against it.
        blob = sim_blob(name)
        reply = f"NTLMv2-SIM {blob} [simulation: not a real hash, not a real credential]"
        sock.sendto(reply.encode(), addr)
        log(
            CAPTURE_LOG,
            f"poisoned answer for '{name}': captured blob NTLMv2-SIM {blob} "
            "(simulated credential material)",
        )


def main() -> None:
    threads = []
    for proto, port in SERVICES:
        th = threading.Thread(target=serve, args=(proto, port), daemon=True)
        th.start()
        threads.append(th)
    for th in threads:
        th.join()


if __name__ == "__main__":
    main()
