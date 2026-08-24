"""Simulated service enumerator and unquoted-path checker. Room target only."""

import os

from flask import Flask, request
from markupsafe import escape

app = Flask(__name__)
FLAG = os.environ["ROOM_FLAG"]

# Simulated SCM query output. One entry deliberately lacks quotes.
SERVICES = [
    ("SimAudioSvc", '"C:\\Program Files\\SimAudio\\audio.exe"'),
    ("UpdateHelperSvc", "C:\\Program Files\\Unquoted Helper\\helper.exe"),
    ("NightlyBackupSvc", '"C:\\Program Files\\Backup Agent\\backup.exe"'),
]

# What CreateProcess would try, in resolution order, for the unquoted entry.
EXPECTED_CHAIN = [
    "c:\\program.exe",
    "c:\\program files\\unquoted.exe",
    "c:\\program files\\unquoted helper\\helper.exe",
]

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Service Enumerator</title>
<style>
body { background:#F7F6F3; font-family:Helvetica,Arial,sans-serif; display:flex; justify-content:center; padding-top:8vh; }
.box { background:#fff; border:1px solid #EAEAEA; border-radius:8px; padding:2.5rem; width:40rem; }
h1 { letter-spacing:-0.02em; font-size:1.35rem; margin-bottom:.6rem; }
table { border-collapse:collapse; width:100%; margin:1rem 0; font-size:.9rem; }
td { border-top:1px solid #EAEAEA; padding:.55rem .4rem; vertical-align:top; }
code, textarea { font-family:ui-monospace,Menlo,monospace; font-size:.85rem; }
textarea { width:100%; min-height:5rem; border:1px solid #EAEAEA; border-radius:6px; padding:.5rem; margin:.4rem 0; }
button { background:#111; color:#fff; border:none; border-radius:6px; padding:.55rem 1rem; cursor:pointer; }
p, li { color:#787774; font-size:.9rem; }
.flag { background:#EDF3EC; color:#346538; border-radius:9999px; padding:.35rem 1rem; display:inline-block; }
.err { background:#FBEBEB; color:#8A3A38; border-radius:9999px; padding:.35rem 1rem; display:inline-block; }
</style></head><body>__BODY__</body></html>"""


def _page(body: str) -> str:
    return PAGE.replace("__BODY__", body)


def _rows():
    return "".join(
        f"<tr><td>{escape(name)}</td><td><code>{escape(path)}</code></td></tr>"
        for name, path in SERVICES
    )


def _normalize(raw: str) -> list[str]:
    parts = raw.replace("\r", "").replace(",", "\n").split("\n")
    out = []
    for part in parts:
        part = part.strip().strip('"')
        if not part:
            continue
        out.append(" ".join(part.casefold().split()))
    return out


@app.get("/healthz")
def healthz():
    return "ok"


@app.get("/")
def home():
    body = f"""
<div class="box">
<h1>Service Enumerator <small>(simulated)</small></h1>
<p>Verbatim query output from this box's simulated Service Control Manager,
the way sc qc would print it on a Windows machine. One of these binPath
values is asking for trouble.</p>
<table><tr><th>Service</th><th>binPath</th></tr>{_rows()}</table>
<p>Think like CreateProcess: for the unquoted path, list every executable
location it would try, in resolution order, last entry being the real binary.
One path per line.</p>
<form method="post" action="/check">
<textarea name="chain" placeholder="one path per line, in order"></textarea>
<button type="submit">Check chain</button>
</form>
</div>"""
    return _page(body)


@app.post("/check")
def check():
    submitted = _normalize(request.form.get("chain", ""))
    if not submitted:
        return _page(
            "<div class='box'><h1>Nothing to check</h1>"
            "<p>The chain field was empty.</p>"
            "<p><a href='/'>Back to the enumerator</a></p></div>"
        )
    if len(submitted) != len(EXPECTED_CHAIN):
        return _page(
            "<div class='box'><h1>Wrong length</h1>"
            "<p>A complete chain has a specific number of candidates; "
            f"you submitted {len(submitted)}. Re-derive it.</p>"
            "<p><a href='/'>Back to the enumerator</a></p></div>"
        )
    if submitted != EXPECTED_CHAIN:
        first_bad = next(
            i for i, (got, want) in enumerate(zip(submitted, EXPECTED_CHAIN)) if got != want
        )
        return _page(
            "<div class='box'><h1>Order or content mismatch</h1>"
            f"<p>Entry {first_bad + 1} does not match resolution semantics.</p>"
            "<p><a href='/'>Back to the enumerator</a></p></div>"
        )
    return _page(
        "<div class='box'><h1>Chain accepted</h1>"
        "<p>You reproduced CreateProcess's search order exactly. Here is the"
        " verification token for this session:</p>"
        f"<span class='flag'>{FLAG}</span></div>"
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
