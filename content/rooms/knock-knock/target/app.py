"""Gatekeeper vault: UDP port-knocking simulation. Room target only."""

import os
import secrets
import socket
import threading
import time

from flask import Flask, Response

app = Flask(__name__)
FLAG = os.environ["ROOM_FLAG"]

KNOCK_SEQUENCE = ((7000, "knock1"), (8000, "knock2"), (9000, "knock3"))
STATUS_PORT = 9999
SEQUENCE_WINDOW_SECONDS = 10.0
VAULT_WINDOW_SECONDS = 60.0

_lock = threading.Lock()
_progress = 0
_vault_token = ""
_vault_until = 0.0


def _register_knock(index: int, payload: str) -> str:
    global _progress, _vault_token, _vault_until
    with _lock:
        expected_port, expected_payload = KNOCK_SEQUENCE[_progress]
        if index == _progress and payload == expected_payload:
            _progress += 1
            if _progress == len(KNOCK_SEQUENCE):
                _vault_token = secrets.token_hex(16)
                _vault_until = time.time() + VAULT_WINDOW_SECONDS
                _progress = 0
                return (
                    f"sequence complete. vault open for {int(VAULT_WINDOW_SECONDS)}s "
                    f"TOKEN={_vault_token}"
                )
            return f"knock {_progress}/{len(KNOCK_SEQUENCE)} accepted on udp/{expected_port}"
        _progress = 0
        return (
            f"out of sequence. next knock: payload {KNOCK_SEQUENCE[0][1]!r} "
            f"to udp/{KNOCK_SEQUENCE[0][0]}"
        )


def _serve_knock(port: int, index: int) -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", port))
    while True:
        data, addr = sock.recvfrom(1024)
        payload = data.decode(errors="replace").strip()
        try:
            reply = _register_knock(index, payload)
        except Exception as exc:  # keep the daemon alive no matter what
            reply = f"gatekeeper error: {exc.__class__.__name__}"
        sock.sendto(reply.encode(), addr)


def _serve_status() -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", STATUS_PORT))
    while True:
        data, addr = sock.recvfrom(1024)
        with _lock:
            if _vault_token and time.time() < _vault_until:
                remaining = max(1, int(_vault_until - time.time()))
                reply = (
                    f"gate OPEN for {remaining}s. knock sequence accepted. "
                    f"present TOKEN={_vault_token} at /vault/<token>"
                )
            else:
                ports = ", ".join(str(p) for p, _ in KNOCK_SEQUENCE)
                reply = (
                    "gate closed. i am the status probe; the gatekeeper listens on "
                    f"udp {ports}. each port wants its own payload in ascending order "
                    f"within {int(SEQUENCE_WINDOW_SECONDS)}s."
                )
        sock.sendto(reply.encode(), addr)


PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Harborview Records Vault</title>
<style>
body { background:#F7F6F3; font-family:Helvetica,Arial,sans-serif; display:flex; justify-content:center; padding-top:12vh; }
.box { background:#fff; border:1px solid #EAEAEA; border-radius:8px; padding:2.5rem; width:30rem; }
h1 { letter-spacing:-0.02em; font-size:1.4rem; margin-bottom:1rem; }
p, li { color:#787774; font-size:.9rem; line-height:1.5; }
code { background:#F7F6F3; padding:.1rem .35rem; border-radius:4px; font-size:.85rem; }
.flag { background:#EDF3EC; color:#346538; border-radius:9999px; padding:.35rem 1rem; display:inline-block; }
</style></head><body>%s</body></html>"""


@app.get("/healthz")
def healthz():
    return "ok"


@app.get("/")
def home():
    return (
        PAGE
        % """
<div class="box">
<h1>Harborview Records Vault</h1>
<p>This appliance keeps its records behind a timed gate. The HTTP vault
endpoint is mounted but it stays sealed until the <code>gatekeeper</code>
daemon announces a valid visitor.</p>
<p>The gatekeeper never answers TCP. It watches three high UDP ports,
expects one short word per port in ascending order, and forgets your
progress if you take longer than ten seconds between knocks.</p>
<p>A read-only status probe runs on <code>udp/9999</code>. It answers any
datagram with the current gate state.</p>
</div>"""
    )


@app.get("/vault/<token>")
def vault(token: str):
    with _lock:
        open_now = bool(_vault_token) and token == _vault_token and time.time() < _vault_until
    if not open_now:
        return Response(
            PAGE
            % """
<div class="box">
<h1>Vault sealed</h1>
<p>The gatekeeper has not admitted this token, or the sixty second
window already closed. Knock again to mint a fresh one.</p>
</div>""",
            status=403,
        )
    return (
        PAGE
        % f"""
<div class="box">
<h1>Vault open</h1>
<p>Welcome, verified knocker. The record of this session is:</p>
<span class="flag">{FLAG}</span>
<p>The gate re-seals automatically.</p>
</div>"""
    )


if __name__ == "__main__":
    for position, (port, _payload) in enumerate(KNOCK_SEQUENCE):
        threading.Thread(target=_serve_knock, args=(port, position), daemon=True).start()
    threading.Thread(target=_serve_status, daemon=True).start()
    app.run(host="0.0.0.0", port=8000, threaded=True)
