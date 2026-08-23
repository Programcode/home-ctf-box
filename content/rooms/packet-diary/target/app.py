"""Case file for the archive appliance incident. Room target only.

Generates a deterministic libpcap capture of a short FTP session at
import time; no live traffic is involved anywhere.
"""

import os
import struct

from flask import Flask, Response, request

app = Flask(__name__)
FLAG = os.environ["ROOM_FLAG"]
FTP_PASSWORD = "maple-syrup-42"

CLIENT_IP = "10.60.0.20"
SERVER_IP = "10.60.0.30"
CONTROL_PORT = 21
EPHEMERAL_PORT = 51515

BASE_TS = 1787510400  # fixed capture start so the artifact is reproducible


def _checksum(data: bytes) -> int:
    if len(data) % 2:
        data += b"\x00"
    total = sum(struct.unpack_from(f">{len(data) // 2}H", data))
    total = (total >> 16) + (total & 0xFFFF)
    return (~total) & 0xFFFF


def _frame(
    payload: bytes, src_port: int, dst_port: int, seq: int, ack: int, from_client: bool, psh: bool
) -> bytes:
    src_ip = CLIENT_IP if from_client else SERVER_IP
    dst_ip = SERVER_IP if from_client else CLIENT_IP
    tcp_flags = 0x18 if psh else 0x10  # PSH|ACK for data, ACK otherwise
    tcp = struct.pack(
        ">HHIIBBHHH",
        src_port,
        dst_port,
        seq,
        ack,
        5 << 4,
        tcp_flags,
        65535,
        0,
        0,
    )
    pseudo = struct.pack(
        "!4s4sBBH",
        bytes(map(int, src_ip.split("."))),
        bytes(map(int, dst_ip.split("."))),
        0,
        6,
        20 + len(payload),
    )
    checksum = _checksum(pseudo + tcp + payload)
    tcp = tcp[:16] + struct.pack(">H", checksum) + tcp[18:]
    total_len = 20 + len(tcp) + len(payload)
    ip = struct.pack(">BBHHHBBH", 0x45, 0, total_len, 0x1234, 0x4000, 64, 6, 0)
    ip += bytes(map(int, src_ip.split("."))) + bytes(map(int, dst_ip.split(".")))
    ip = ip[:10] + struct.pack(">H", _checksum(ip)) + ip[12:]
    return b"\x02\x00\x00\x00\x00\x01\x02\x00\x00\x00\x00\x02\x08\x00" + ip + tcp + payload


def _segment(text: str, seq: int, ack: int, from_client: bool) -> tuple[bytes, int]:
    payload = text.encode()
    frame = _frame(
        payload,
        EPHEMERAL_PORT if from_client else CONTROL_PORT,
        CONTROL_PORT if from_client else EPHEMERAL_PORT,
        seq,
        ack,
        from_client,
        psh=True,
    )
    return frame, seq + len(payload)


def build_capture() -> bytes:
    out = [struct.pack("<IHHiIII", 0xA1B2C3D4, 2, 4, 0, 0, 262144, 1)]

    def emit(frame: bytes, index: int) -> None:
        ts = BASE_TS + index
        out.append(struct.pack("<IIII", ts, index * 137, len(frame), len(frame)))
        out.append(frame)

    commands = (
        "USER archivist",
        f"PASS {FTP_PASSWORD}",
        "PORT 10,60,0,20,200,13",
        "STOR diary-entry-august.txt",
        "QUIT",
    )
    responses = (
        "220 diary-archive.internal FTP server ready",
        "331 Password required for archivist",
        "230 User archivist logged in",
        "200 PORT command successful",
        "226 Transfer complete",
        "221 Goodbye",
    )
    cseq, sseq = 1000, 5000
    ack_c, ack_s = 5001, 1001
    index = 0
    for command in commands:
        frame, cseq_next = _segment(command + "\r\n", cseq, ack_s, True)
        emit(frame, index)
        index += 1
        ack_s = cseq_next
    for response in responses:
        frame, sseq_next = _segment(response + "\r\n", sseq, ack_c, False)
        emit(frame, index)
        index += 1
        ack_c = sseq_next
    return b"".join(out)


CAPTURE_BYTES = build_capture()

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Case 2026-08-19: archive appliance</title>
<style>
body { background:#F7F6F3; font-family:Helvetica,Arial,sans-serif; display:flex; justify-content:center; padding-top:12vh; }
.box { background:#fff; border:1px solid #EAEAEA; border-radius:8px; padding:2.5rem; width:30rem; }
h1 { letter-spacing:-0.02em; font-size:1.35rem; margin-bottom:1rem; }
p, li { color:#787774; font-size:.9rem; line-height:1.55; }
code { background:#F7F6F3; padding:.1rem .35rem; border-radius:4px; font-size:.85rem; }
.flag { background:#EDF3EC; color:#346538; border-radius:9999px; padding:.35rem 1rem; display:inline-block; }
a { color:#111; }
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
<h1>Case 2026-08-19: archive appliance</h1>
<p>During a routine review the archive appliance was found still
speaking plain FTP on the operations segment. One control session was
captured before the service was disabled.</p>
<p>Evidence: <a href="/evidence/capture.pcap">capture.pcap</a>
(raw libpcap, Ethernet/IPv4/TCP).</p>
<p>The report desk accepts the credential the session leaked:
<code>GET /report?password=...</code>. A verified password closes the
case and prints the finding.</p>
</div>"""
    )


@app.get("/evidence/capture.pcap")
def evidence():
    return Response(
        CAPTURE_BYTES,
        mimetype="application/vnd.tcpdump.pcap",
        headers={"Content-Disposition": "attachment; filename=capture.pcap"},
    )


@app.get("/report")
def report():
    password = request.args.get("password", "")
    if password == FTP_PASSWORD:
        return (
            PAGE
            % f"""
<div class="box">
<h1>Report accepted</h1>
<p>Credential confirmed against the capture. Finding recorded for case
2026-08-19: FTP control channel exposed a working password.</p>
<span class="flag">{FLAG}</span>
<p>Remediation note: retire cleartext protocols or tunnel them.</p>
</div>"""
        )
    return (
        PAGE
        % """
<div class="box">
<h1>Report rejected</h1>
<p>The submitted value does not match the credential visible in the
capture. Re-read the login exchange on the control channel.</p>
</div>""",
        403,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, threaded=True)
