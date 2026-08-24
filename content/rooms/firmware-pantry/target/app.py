"""PantryGate firmware desk: synthetic firmware extraction sim. Room target only.

The image is assembled at import time from strings plus stdlib
tarfile/lzma with a documented stub-magic-archive layout. It is not a
real vendor image, carries no executable code, and every credential is
simulation scaffolding.
"""

import hashlib
import io
import lzma
import os
import tarfile

from flask import Flask, Response, request

app = Flask(__name__)
FLAG = os.environ["ROOM_FLAG"]

MAGIC = b"FSQSIM1\x00"
STUB_LEN = 512

WORD_A = [
    "granary",
    "silage",
    "chaff",
    "winnow",
    "thresh",
    "barley",
    "oats",
    "rye",
    "millet",
    "sorghum",
    "trough",
    "hopper",
    "silo",
    "crib",
    "husk",
    "kernel",
    "bran",
    "grist",
    "millstone",
    "flour",
]
WORD_B = [
    "gate",
    "pantry",
    "loam",
    "harvest",
    "cellar",
    "root",
    "store",
    "barn",
    "field",
    "fallow",
    "clover",
    "alfalfa",
    "canola",
    "maize",
]
WORDS = sorted(f"{a}-{b}" for a in WORD_A for b in WORD_B)

_PW_SEED = hashlib.sha256(b"firmware-pantry|admin-password").digest()
ADMIN_PASSWORD = WORDS[int.from_bytes(_PW_SEED[:4], "big") % len(WORDS)]
ADMIN_HASH = hashlib.sha256(ADMIN_PASSWORD.encode()).hexdigest()

STUB_TEXT = """PANTRY-GATE PG-110 GATE CONTROLLER FIRMWARE 4.2 SIMULATED NOTES
layout:   vendor stub 512 bytes | magic FSQSIM1 8 bytes | tar.xz rootfs
payload:  starts at offset 512 from image start, immediately after FSQSIM1
extract:  slice there then tar -xJf, or scan for xz magic fd 37 7a 58 5a 00
contents: etc/shadow-sim, etc/passwd-sim, etc/release-notes.txt,
          usr/bin/pantryctl, README-SIM.txt
note:     synthetic teaching artifact; no vendor code, signatures, devices
""".encode()

STUB = STUB_TEXT + b" " * (STUB_LEN - len(STUB_TEXT))
assert len(STUB) == STUB_LEN


def build_rootfs() -> bytes:
    files = {
        "etc/shadow-sim": (
            "root:!::0:::::\n"
            f"admin:$sim${ADMIN_HASH}:19920:0:99999:7:::\n"
            "daemon:*:19920:0:99999:7:::\n"
        ),
        "etc/passwd-sim": (
            "root:x:0:0:root:/root:/bin/sh\n"
            "admin:x:1000:1000:PantryGate admin:/var/empty:/sbin/nologin\n"
        ),
        "etc/release-notes.txt": STUB_TEXT.decode(),
        "usr/bin/pantryctl": (
            "#!/bin/sh\n"
            'case "$1" in\n'
            "  open) echo 'door open (simulated)' ;;\n"
            "  close) echo 'door closed (simulated)' ;;\n"
            "  status) cat /etc/release-notes.txt | head -3 ;;\n"
            "esac\n"
        ),
        "README-SIM.txt": (
            "This root filesystem is a synthetic teaching artifact.\n"
            "Nothing here executes on real hardware and no credential\n"
            "is used anywhere outside this room.\n"
        ),
    }
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tar:
        for name, text in sorted(files.items()):
            data = text.encode()
            info = tarfile.TarInfo(name)
            info.size = len(data)
            info.mode = 0o755 if name.startswith("usr/") else 0o644
            tar.addfile(info, io.BytesIO(data))
    return lzma.compress(buf.getvalue())


ROOTFS_XZ = build_rootfs()
FIRMWARE = STUB + MAGIC + ROOTFS_XZ

PAGE_TMPL = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>PantryGate firmware desk</title><style>
body {{ background:#F7F6F3; font-family:Helvetica,Arial,sans-serif; display:flex; justify-content:center; padding-top:8vh; }}
.wrap {{ width:46rem; padding-bottom:4rem; }}
.box {{ background:#fff; border:1px solid #EAEAEA; border-radius:8px; padding:1.5rem 2rem; margin-bottom:.8rem; }}
code, pre {{ background:#F7F6F3; border-radius:6px; padding:.15rem .4rem; font-size:.82rem; overflow-wrap:anywhere; }}
h1 {{ letter-spacing:-0.02em; font-size:1.35rem; }} h2 {{ font-size:1rem; }}
p, li {{ color:#787774; font-size:.9rem; line-height:1.55; }}
.disclosure {{ background:#FDF3E7; border:1px solid #EAD3AE; }}
input {{ width:100%; padding:.45rem; border:1px solid #EAEAEA; border-radius:6px; margin-bottom:.5rem; }}
button {{ background:#111; color:#fff; border:none; border-radius:6px; padding:.5rem 1rem; cursor:pointer; }}
.good {{ color:#346538; }}
</style></head><body><div class="wrap">{}</div></body></html>"""

HOME = f"""
<div class="box disclosure">
<h2>This is a simulation</h2>
<p>The image below is written by this service from plain strings and
stdlib compression. It is not a real vendor update, contains no
machine code, and its shadow entry uses a deliberately simple hash
convention so the exercise stays deterministic. Real firmware work
starts exactly here though: pull the package, find the embedded
filesystem, read what the vendor shipped.</p>
</div>
<div class="box">
<h1>Firmware 4.2 release notes (PG-110)</h1>
<pre>{STUB_TEXT.decode()}</pre>
<p>Evidence shelf:</p>
<ul>
<li><a href="/evidence/firmware.bin">firmware.bin</a>, the full container</li>
<li><a href="/evidence/wordlist.txt">wordlist.txt</a>, candidate passwords for the offline audit</li>
</ul>
</div>
<div class="box">
<h2>Admin desk</h2>
<form method="post" action="/admin/login">
<input name="user" placeholder="user">
<input name="password" placeholder="password">
<button type="submit">Sign in</button>
</form>
</div>
"""


@app.get("/healthz")
def healthz():
    return "ok"


@app.get("/")
def home():
    return PAGE_TMPL.format(HOME)


@app.get("/evidence/firmware.bin")
def firmware():
    return Response(
        FIRMWARE,
        mimetype="application/octet-stream",
        headers={"Content-Disposition": "attachment; filename=firmware.bin"},
    )


@app.get("/evidence/wordlist.txt")
def wordlist():
    return Response(
        ("\n".join(WORDS) + "\n").encode(),
        mimetype="text/plain",
        headers={"Content-Disposition": "attachment; filename=wordlist.txt"},
    )


@app.post("/admin/login")
def admin_login():
    user = request.form.get("user", "")
    password = request.form.get("password", "")
    digest = hashlib.sha256(password.encode()).hexdigest()
    if user == "admin" and hmac_compare(digest, ADMIN_HASH):
        body = """
<div class="box">
<h1 class="good">Admin session opened</h1>
<p>Credential recovered from the shipped shadow database. Audit filed:
the gate controller publishes password-equivalent material inside its
update image, and the scheme has no salt or stretching.</p>
<p><code>{}</code></p>
<p>Remediation note: never ship verifiable credentials inside update
packages, and store only slow, salted hashes when credentials must
exist.</p>
</div>"""
        return PAGE_TMPL.format(body.format(FLAG))
    return PAGE_TMPL.format("""
<div class="box">
<h1>Login rejected</h1>
<p>The submitted pair does not satisfy the shadow database. Re-check
which file holds admin's entry and which hash convention the $sim$
marker promises.</p>
</div>"""), 403


def hmac_compare(left: str, right: str) -> bool:
    import hmac as _hmac

    return _hmac.compare_digest(left.encode(), right.encode())


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, threaded=True)
