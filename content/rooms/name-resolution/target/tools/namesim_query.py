#!/usr/bin/env python3
"""Send a simulated LLMNR/NBT-NS name query to the local responder-sim.

Room tool for name-resolution. The packet format is a plain text
stand-in for the real protocols; nothing here can affect anything
beyond this container's loopback interface.
"""

import argparse
import socket


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="namesim_query",
        description="Query the room's responder-sim on loopback (simulation).",
    )
    parser.add_argument("--proto", choices=["llmnr", "nbtns"], default="llmnr")
    parser.add_argument("--name", required=True, help="single-label name, e.g. FILESRV01")
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()

    port = 5355 if args.proto == "llmnr" else 137
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(2.0)
    sock.sendto(f"QRY|{args.proto.upper()}|{args.name}".encode(), (args.host, port))
    try:
        data, addr = sock.recvfrom(2048)
    except socket.timeout:
        print("no response within 2s; this name drew no poisoning attempt")
        return 1
    print(f"reply from {addr[0]}:{addr[1]}:")
    print(data.decode(errors="replace"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
