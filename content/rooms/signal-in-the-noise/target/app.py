"""Garage remote case: deterministic OOK IQ capture sim. Room target only.

No RF hardware, transmission, or real garage exists. Samples come from
Python integer math with a fixed seed schedule, and the spectrum plot
is a PNG written by hand with zlib so the whole room stays stdlib.
"""

import hashlib
import os
import struct
import zlib

from flask import Flask, Response, request

app = Flask(__name__)
FLAG = os.environ["ROOM_FLAG"]

SAMPLES_PER_BIT = 8
AMP_ONE = 12000
AMP_ZERO = 400
THRESHOLD = 3000
PREAMBLE = 0xAA  # bits 1,0,1,0,1,0,1,0 MSB first
FRAMES = 6
GAP_BITS = 3

STATIC_CODE = int.from_bytes(hashlib.sha256(b"signal-in-the-noise|static-code").digest()[:4], "big")
ROLL_START = 0x00C0FFEE


def frame_bits(roll: int) -> list[int]:
    word = (PREAMBLE << 64) | (STATIC_CODE << 32) | roll
    return [(word >> (71 - i)) & 1 for i in range(72)]


def build_samples() -> list[int]:
    iq: list[int] = []
    for lead in range(16):
        iq.append((AMP_ZERO if lead % 2 else AMP_ZERO // 2, ((lead % 13) - 6) * 30))
    for n in range(FRAMES):
        for bit in frame_bits(ROLL_START + n):
            level = AMP_ONE if bit else AMP_ZERO
            for _ in range(SAMPLES_PER_BIT):
                iq.append((level, 0))
        if n != FRAMES - 1:
            for g in range(GAP_BITS * SAMPLES_PER_BIT):
                iq.append((AMP_ZERO, ((g % 11) - 5) * 24))
    for tail in range(16):
        iq.append((AMP_ZERO, ((tail % 7) - 3) * 20))
    return iq


SAMPLES = build_samples()
IQ_BYTES = b"".join(struct.pack("<hh", i, q) for i, q in SAMPLES)


def write_png(width: int, height: int, rows: list[bytes]) -> bytes:
    def chunk(tag: bytes, payload: bytes) -> bytes:
        return (
            struct.pack(">I", len(payload))
            + tag
            + payload
            + struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF)
        )

    raw = b"".join(b"\x00" + row for row in rows)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )


def build_spectrum() -> bytes:
    width, height = 960, 240
    baseline = height - 30
    bg = bytes((247, 246, 243))
    ink = bytes((17, 17, 17))
    warn = bytes((180, 83, 9))
    grid = [bytearray(bg * width) for _ in range(height)]
    scale = (height - 60) / 16384.0

    threshold_y = baseline - int(THRESHOLD * scale)
    for x in range(width):
        grid[threshold_y][x * 3 : x * 3 + 3] = warn

    peak_per_column = []
    span = len(SAMPLES) / width
    for col in range(width):
        start, end = int(col * span), max(int((col + 1) * span), int(col * span) + 1)
        peak_per_column.append(max(abs(i) for i, _ in SAMPLES[start:end]))

    prev_y = baseline - int(min(peak_per_column[0], 16384) * scale)
    for col, peak in enumerate(peak_per_column):
        y = baseline - int(min(peak, 16384) * scale)
        step = 1 if y >= prev_y else -1
        for yy in range(prev_y, y + step, step):
            grid[yy][col * 3 : col * 3 + 3] = ink
        prev_y = y
    for x in range(width):
        grid[baseline][x * 3 : x * 3 + 3] = ink

    return write_png(width, height, [bytes(row) for row in grid])


SPECTRUM_PNG = build_spectrum()

PAGE_TMPL = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Case 2026-08-23: garage remote</title><style>
body {{ background:#F7F6F3; font-family:Helvetica,Arial,sans-serif; display:flex; justify-content:center; padding-top:8vh; }}
.wrap {{ width:46rem; padding-bottom:4rem; }}
.box {{ background:#fff; border:1px solid #EAEAEA; border-radius:8px; padding:1.5rem 2rem; margin-bottom:.8rem; }}
code, pre {{ background:#F7F6F3; border-radius:6px; padding:.15rem .4rem; font-size:.82rem; overflow-wrap:anywhere; }}
h1 {{ letter-spacing:-0.02em; font-size:1.35rem; }} h2 {{ font-size:1rem; }}
p, li {{ color:#787774; font-size:.9rem; line-height:1.55; }}
.disclosure {{ background:#FDF3E7; border:1px solid #EAD3AE; }}
.good {{ color:#346538; }} img {{ max-width:100%; border:1px solid #EAEAEA; border-radius:6px; }}
</style></head><body><div class="wrap">{}</div></body></html>"""

HOME = """
<div class="box disclosure">
<h2>This is a simulation</h2>
<p>No radio transmitted anything here. The capture was computed by
this service from integer constants, the modulation is deliberately
simple on-off keying, and the garage opener is an endpoint inside this
container. The artifact and the decoding habits are what transfer to
real RF work.</p>
</div>
<div class="box">
<h1>Case 2026-08-23: cloned remote complaint</h1>
<p>A resident reports their garage remote opening doors it should not.
A single press was captured off a bench receiver and exported as raw
samples.</p>
<p>Evidence:</p>
<ul>
<li><a href="/evidence/capture.iq">capture.iq</a>, interleaved signed 16-bit
little-endian pairs, I then Q, no header.</li>
<li><a href="/evidence/spectrum.png">spectrum.png</a>, envelope plot of the same
capture.</li>
</ul>
<p>Receiver notes from the bench: on-off keying, each bit spans exactly
8 samples, amplitude above roughly 3000 counts reads as one. The bench
opener accepts replays at <code>GET /garage/open?code=&lt;hex&gt;</code>.</p>
</div>
"""


@app.get("/healthz")
def healthz():
    return "ok"


@app.get("/")
def home():
    return PAGE_TMPL.format(HOME)


@app.get("/evidence/capture.iq")
def capture():
    return Response(
        IQ_BYTES,
        mimetype="application/octet-stream",
        headers={"Content-Disposition": "attachment; filename=capture.iq"},
    )


@app.get("/evidence/spectrum.png")
def spectrum():
    return Response(SPECTRUM_PNG, mimetype="image/png")


@app.get("/garage/open")
def garage_open():
    code = request.args.get("code", "").strip().upper()
    if code == f"{STATIC_CODE:08X}":
        return PAGE_TMPL.format(f"""
<div class="box">
<h1 class="good">Door opened</h1>
<p>The bench receiver accepted static code <code>{STATIC_CODE:08X}</code>,
confirming the remote's identity section survives replay because its
rolling half is decorative here. Finding filed: fixed-code section
reusable within the observed window.</p>
<p><code>{FLAG}</code></p>
</div>""")
    return PAGE_TMPL.format("""
<div class="box">
<h1>Receiver ignored you</h1>
<p>That code does not match the remote's constant section. Check which
32-bit word never changes across the six repetitions before blaming
your endianness.</p>
</div>"""), 403


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, threaded=True)
