"""Intended-path solver: slice the archive, read shadow-sim, crack, log in."""

import hashlib
import io
import re
import tarfile

import httpx

from openrange.content.solver import SolveResult, TaskResult, find_flags

SHADOW_RE = re.compile(rb"^admin:\$sim\$([0-9a-f]{64}):", re.MULTILINE)
XZ_MAGIC = b"\xfd7zXZ\x00"


def solve(ctx) -> SolveResult:  # type: ignore[no-untyped-def]
    expected = ctx.expected_flags["crack-and-login"]
    client = httpx.Client(base_url=ctx.url(), timeout=10)

    image = client.get("/evidence/firmware.bin").content
    stub = image[:512]
    assert b"FSQSIM1" in stub and b"tar" in stub.lower(), "stub should document the layout"

    # The literal magic also appears inside the stub prose, so validate
    # candidates like a carver would: the true boundary is the FSQSIM1
    # occurrence immediately followed by the xz stream signature.
    payload = None
    cursor = image.find(b"FSQSIM1")
    while cursor != -1:
        candidate = image[cursor + 8 :]
        if candidate.startswith(XZ_MAGIC):
            payload = candidate
            break
        cursor = image.find(b"FSQSIM1", cursor + 1)
    assert payload is not None, "no FSQSIM1 occurrence backed by an xz stream"
    assert payload.startswith(XZ_MAGIC), "archive must begin with the xz signature"

    with tarfile.open(fileobj=io.BytesIO(payload), mode="r:xz") as tar:
        shadow = tar.extractfile("etc/shadow-sim").read()
        names = tar.getnames()
    match = SHADOW_RE.search(shadow)
    assert match and "usr/bin/pantryctl" in names, f"shadow-sim missing admin entry in {names}"
    target_hash = match.group(1).decode()

    wordlist = client.get("/evidence/wordlist.txt").text.splitlines()
    cracked = [w for w in wordlist if hashlib.sha256(w.encode()).hexdigest() == target_hash]
    assert len(cracked) == 1, f"expected exactly one crack, got {cracked}"

    resp = client.post("/admin/login", data={"user": "admin", "password": cracked[0]})
    client.close()
    flags = find_flags(resp.text)
    captured = flags[0] if flags else None
    ok = captured == expected
    detail = None if ok else f"cracked={cracked} status={resp.status_code}"
    return SolveResult(
        results=[TaskResult(task_id="crack-and-login", ok=ok, captured=captured, detail=detail)]
    )
