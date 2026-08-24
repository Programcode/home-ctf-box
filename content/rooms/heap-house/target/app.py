"""Heap House: deterministic tcache-poisoning teaching simulator. Room target only.

No real allocator, binary, or memory corruption lives here. The heap is
a Python dictionary modeling qword slots; every mechanic mirrors glibc
tcache behavior that the lesson maps explicitly.
"""

import os

from flask import Flask, jsonify, request

app = Flask(__name__)
FLAG = os.environ["ROOM_FLAG"]

MASK64 = (1 << 64) - 1
WIN_ADDR = 0x20000
WIN_MAGIC = 0xC0FFEE000001
CLASSES = (64, 128, 256)
CLASS_BASE = {64: 0x10040, 128: 0x20040, 256: 0x30040}


class HeapState:
    def __init__(self) -> None:
        self.chunks: dict[str, dict] = {}
        self.bins: dict[int, list[int]] = {c: [] for c in CLASSES}
        self.mem: dict[int, int] = {}
        self.bump: dict[int, int] = {c: CLASS_BASE[c] for c in CLASSES}
        self.next_id = 1
        self.forge_id = 1
        self.events: list[str] = []
        self.crashed: str | None = None

    def log(self, text: str) -> None:
        self.events.append(text)
        del self.events[:-12]

    def addr_of(self, ident: str) -> int | None:
        chunk = self.chunks.get(ident)
        return None if chunk is None else chunk["addr"]


STATE = HeapState()


def hx(value: int) -> str:
    return f"0x{value:X}"


def chunk_view(state: HeapState) -> list[dict]:
    rows = []
    for ident, chunk in state.chunks.items():
        rows.append(
            {
                "id": ident,
                "addr": hx(chunk["addr"]),
                "size_class": chunk["class"],
                "state": chunk["state"],
                "forged": chunk["forged"],
            }
        )
    return rows


def bin_view(state: HeapState) -> dict[str, list[dict]]:
    out = {}
    for size, entries in state.bins.items():
        row = []
        for addr in entries:
            ident = next((i for i, c in state.chunks.items() if c["addr"] == addr), None)
            row.append(
                {"addr": hx(addr), "owner": ident or "unmapped", "fd": hx(state.mem.get(addr, 0))}
            )
        out[str(size)] = row
    return out


@app.get("/healthz")
def healthz():
    return "ok"


PAGE_TMPL = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Heap House</title><style>
body {{ background:#F7F6F3; font-family:Helvetica,Arial,sans-serif; display:flex; justify-content:center; padding-top:6vh; }}
.wrap {{ width:46rem; padding-bottom:4rem; }}
.box {{ background:#fff; border:1px solid #EAEAEA; border-radius:8px; padding:1.5rem 2rem; margin-bottom:.8rem; }}
code, pre {{ background:#F7F6F3; border-radius:6px; padding:.15rem .4rem; font-size:.82rem; overflow-wrap:anywhere; }}
h1 {{ letter-spacing:-0.02em; font-size:1.35rem; }} h2 {{ font-size:1rem; }}
p, li {{ color:#787774; font-size:.9rem; line-height:1.55; }}
.disclosure {{ background:#FDF3E7; border:1px solid #EAD3AE; }}
</style></head><body><div class="wrap">{}</div></body></html>"""

HOME = """
<div class="box disclosure">
<h2>This is a simulator</h2>
<p>Nothing here executes real exploits or touches real memory. The heap
is a Python dictionary inside one disposable container. Addresses are
sequential integers chosen by the service. The use-after-free bug is
installed on purpose so you can study the tcache poisoning state machine
safely. The lesson file maps every step to what glibc would really do,
including safe-linking, which this room deliberately does not emulate.</p>
</div>
<div class="box">
<h1>The House allocator</h1>
<p>A tiny bump allocator with a tcache-like fast path. Size classes are
64, 128 and 256 bytes. Fresh allocations come from a per-class bump
area starting at <code>0x10040</code>, <code>0x20040</code>,
<code>0x30040</code>. Frees push chunk addresses onto a per-class LIFO
bin and store the previous top address as that chunk's
<code>fd</code> at data offset 0. Malloc pops the bin top and promotes
whatever its fd slot says.</p>
<p><b>The bug:</b> freed chunks remain readable and writable. That is
the entire challenge.</p>
<p>The <code>win</code> variable lives at <code>0x20000</code>. Make it
hold <code>0xC0FFEE000001</code> and <code>GET /api/win</code> prints
your flag.</p>
<h2>Endpoints</h2>
<pre>
POST /api/malloc  {{"size": 64}}            -&gt; id, addr, source
POST /api/free   {{"id": "c1"}}             -&gt; bin push
POST /api/write  {{"id"|"addr", "offset", "value"}} -&gt; qword store
POST /api/read   {{"id"|"addr", "offset"}}          -&gt; qword load
GET  /api/state                             -&gt; full arena dump
GET  /api/win                               -&gt; win check
POST /api/reset                              -&gt; fresh house
</pre>
<p>Offsets are byte offsets into chunk data, multiples of 8, range 0
to 56. Values are integers (decimal or 0x hex). Writes to freed chunks
succeed and are labeled <code>uaf-write</code> in the event log, which
is your confirmation the dangling primitive fired.</p>
</div>
"""


@app.get("/")
def home():
    return PAGE_TMPL.format(HOME)


def _abort(state: HeapState, reason: str):
    state.crashed = reason
    state.log("allocator aborted: " + reason)
    return jsonify({"error": reason, "crashed": True}), 400


@app.post("/api/malloc")
def do_malloc():
    state = STATE
    if state.crashed:
        return jsonify({"error": state.crashed, "crashed": True}), 400
    body = request.get_json(silent=True) or {}
    size = body.get("size")
    if not isinstance(size, int) or size <= 0 or size > 256:
        return jsonify({"error": "size must be an integer in 1..256"}), 400
    size_class = next((c for c in CLASSES if size <= c), None)
    assert size_class is not None
    entries = state.bins[size_class]
    if entries:
        top = entries.pop()
        fd = state.mem.get(top, 0)
        rest = entries
        promoted = None
        if fd and (not rest or rest[-1] != fd):
            if fd == WIN_ADDR or fd % 16 == 0:
                rest.append(fd)
                promoted = fd
                state.log(f"malloc promotes poisoned fd {hx(fd)}")
            else:
                return _abort(state, f"malloc(): unaligned tcache chunk detected {hx(fd)}")
        owner = next((i for i, c in state.chunks.items() if c["addr"] == top), None)
        if owner is None:
            if top % 16 != 0 or top == 0:
                return _abort(state, f"malloc(): unaligned tcache chunk detected {hx(top)}")
            owner = f"f{state.forge_id}"
            state.forge_id += 1
            state.chunks[owner] = {
                "addr": top,
                "class": size_class,
                "state": "allocated",
                "forged": True,
            }
            state.log(f"malloc forged {owner} at {hx(top)}")
        else:
            state.chunks[owner]["state"] = "allocated"
            state.log(f"malloc recycles {owner}")
        resp = {
            "id": owner,
            "addr": hx(top),
            "size_class": size_class,
            "source": "tcache",
        }
        if promoted is not None:
            resp["promoted_fd"] = hx(promoted)
        return jsonify(resp)
    addr = state.bump[size_class]
    state.bump[size_class] += size_class
    ident = f"c{state.next_id}"
    state.next_id += 1
    state.chunks[ident] = {"addr": addr, "class": size_class, "state": "allocated", "forged": False}
    state.log(f"malloc fresh {ident} at {hx(addr)} class {size_class}")
    return jsonify({"id": ident, "addr": hx(addr), "size_class": size_class, "source": "fresh"})


@app.post("/api/free")
def do_free():
    state = STATE
    if state.crashed:
        return jsonify({"error": state.crashed, "crashed": True}), 400
    body = request.get_json(silent=True) or {}
    ident = body.get("id", "")
    chunk = state.chunks.get(ident)
    if chunk is None:
        return jsonify({"error": f"unknown chunk {ident}"}), 404
    if chunk["state"] == "freed":
        return jsonify({"error": "double free detected in tcache (simulated)"}), 400
    chunk["state"] = "freed"
    bin_entries = state.bins[chunk["class"]]
    prev_top = bin_entries[-1] if bin_entries else 0
    state.mem[chunk["addr"]] = prev_top
    bin_entries.append(chunk["addr"])
    state.log(f"free {ident} -> bin[{chunk['class']}] fd={hx(prev_top)}")
    return jsonify(
        {
            "freed": ident,
            "bin": [hx(a) for a in bin_entries],
            "fd_slot": hx(prev_top),
            "note": "chunk stays readable and writable: the intentional UAF window",
        }
    )


def _resolve(body: dict) -> tuple[int | None, str]:
    if "id" in body:
        ident = body.get("id", "")
        chunk = STATE.chunks.get(ident)
        if chunk is None:
            return None, f"unknown chunk {ident}"
        return chunk["addr"], ""
    raw = str(body.get("addr", ""))
    try:
        return int(raw, 16) if raw.lower().startswith("0x") else int(raw, 16), ""
    except ValueError:
        return None, f"bad address {raw!r}"


@app.post("/api/write")
def do_write():
    state = STATE
    if state.crashed:
        return jsonify({"error": state.crashed, "crashed": True}), 400
    body = request.get_json(silent=True) or {}
    base, err = _resolve(body)
    if base is None:
        return jsonify({"error": err}), 404
    offset = body.get("offset", 0)
    if not isinstance(offset, int) or offset < 0 or offset > 56 or offset % 8:
        return jsonify({"error": "offset must be a multiple of 8 in 0..56"}), 400
    try:
        value = int(str(body.get("value", "")), 0)
    except ValueError:
        return jsonify({"error": "value must be an integer"}), 400
    if not 0 <= value <= MASK64:
        return jsonify({"error": "value must fit 64 bits"}), 400
    uaf = any(c["addr"] == base and c["state"] == "freed" for c in state.chunks.values())
    state.mem[base + offset] = value
    label = "uaf-write" if uaf else "write"
    state.log(f"{label} {hx(base)}+{offset:#x} <- {hx(value)}")
    return jsonify({"wrote": hx(base + offset), "value": hx(value), "kind": label})


@app.post("/api/read")
def do_read():
    body = request.get_json(silent=True) or {}
    base, err = _resolve(body)
    if base is None:
        return jsonify({"error": err}), 404
    offset = body.get("offset", 0)
    if not isinstance(offset, int) or offset < 0 or offset > 56 or offset % 8:
        return jsonify({"error": "offset must be a multiple of 8 in 0..56"}), 400
    return jsonify({"at": hx(base + offset), "value": hx(STATE.mem.get(base + offset, 0))})


@app.get("/api/state")
def do_state():
    state = STATE
    return jsonify(
        {
            "win_addr": hx(WIN_ADDR),
            "win_magic": hx(WIN_MAGIC),
            "win_value": hx(state.mem.get(WIN_ADDR, 0)),
            "chunks": chunk_view(state),
            "bins": bin_view(state),
            "events": state.events,
            "crashed": state.crashed,
        }
    )


@app.get("/api/win")
def do_win():
    value = STATE.mem.get(WIN_ADDR, 0)
    out = {"win_addr": hx(WIN_ADDR), "win_value": hx(value), "expected": hx(WIN_MAGIC)}
    if value == WIN_MAGIC:
        out.update({"won": True, "flag": FLAG})
    else:
        out["won"] = False
    return jsonify(out)


@app.post("/api/reset")
def do_reset():
    global STATE
    STATE = HeapState()
    return jsonify({"reset": True})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, threaded=True)
