#!/usr/bin/env python3
"""Anonymous file drop: a small FTP-like line protocol on port 2121.

Guests log in with USER anonymous / PASS guest@ and get read-only
access to /srv/ftpd. File contents are sent on the control channel;
this is a teaching simulator, not an RFC 959 implementation.
"""

import os
import socket
import threading

ROOT = "/srv/ftpd"
PORT = 2121
BANNER = (
    "2121 Services Everywhere anonymous file drop ready.\n"
    "Line protocol: USER, PASS, LIST [dir], CWD <dir>, RETR <file>, QUIT.\n"
)

state = threading.local()


def resolve(virtual: str) -> str:
    cleaned = os.path.normpath("/" + virtual.strip()).lstrip("/")
    return os.path.join(ROOT, cleaned)


def safe_path(path: str) -> str | None:
    real = os.path.realpath(path)
    if real == os.path.realpath(ROOT) or real.startswith(os.path.realpath(ROOT) + os.sep):
        return real
    return None


def handle(conn: socket.socket) -> None:
    conn.sendall(BANNER.encode())
    cwd = "/"
    reader = conn.makefile("r", encoding="utf-8", errors="replace", newline="\n")
    try:
        for raw in reader:
            line = raw.strip()
            if not line:
                continue
            verb, _, arg = line.partition(" ")
            verb = verb.upper()

            if verb in ("USER",):
                name = arg or "anonymous"
                if name == "anonymous":
                    state.user = "anonymous"
                    conn.sendall(b"331 guest access, send PASS guest@\n")
                else:
                    conn.sendall(b"530 only anonymous access is supported\n")
            elif verb == "PASS":
                if getattr(state, "user", None) != "anonymous":
                    conn.sendall(b"503 send USER anonymous first\n")
                elif arg in ("guest@", "guest"):
                    state.authed = True
                    conn.sendall(b"230 guest session open, read only\n")
                else:
                    conn.sendall(b"530 wrong password for guest access\n")
            elif verb == "SYST":
                conn.sendall(b"215 UNIX Type: L8 (simulator)\n")
            elif verb == "PWD":
                if not getattr(state, "authed", False):
                    conn.sendall(b"530 login first\n")
                else:
                    conn.sendall(f'257 "{cwd}" is the current directory\n'.encode())
            elif verb == "CWD":
                if not getattr(state, "authed", False):
                    conn.sendall(b"530 login first\n")
                    continue
                target = safe_path(resolve(arg))
                if target and os.path.isdir(target):
                    cwd = "/" + os.path.relpath(target, ROOT)
                    conn.sendall(b"250 directory changed\n")
                else:
                    conn.sendall(b"550 no such directory\n")
            elif verb == "LIST":
                if not getattr(state, "authed", False):
                    conn.sendall(b"530 login first\n")
                    continue
                target = safe_path(resolve(arg or cwd))
                if not target or not os.path.isdir(target):
                    conn.sendall(b"550 no such directory\n")
                    continue
                lines = []
                for name in sorted(os.listdir(target)):
                    full = os.path.join(target, name)
                    kind = "dir " if os.path.isdir(full) else "file"
                    lines.append(f"- {kind} {name}")
                body = "".join(f"  {ln}\n" for ln in lines) + "226 list complete\n"
                conn.sendall(body.encode())
            elif verb == "RETR":
                if not getattr(state, "authed", False):
                    conn.sendall(b"530 login first\n")
                    continue
                target = safe_path(resolve(arg))
                if not target or not os.path.isfile(target):
                    conn.sendall(b"550 no such file\n")
                    continue
                try:
                    with open(target, encoding="utf-8") as fh:
                        data = fh.read()
                except OSError:
                    conn.sendall(b"550 file unreadable\n")
                    continue
                payload = "--- begin file ---\n" + data
                if not payload.endswith("\n"):
                    payload += "\n"
                payload += "--- end file ---\n226 transfer done\n"
                conn.sendall(payload.encode())
            elif verb == "QUIT":
                conn.sendall(b"221 bye\n")
                break
            else:
                conn.sendall(b"502 unsupported command\n")
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
