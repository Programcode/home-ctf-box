"""Intended-path solver: parse mail.eml with the stdlib and answer the quiz."""

import re
from email import policy
from email.parser import BytesParser

import httpx

from openrange.content.solver import SolveResult, TaskResult, find_flags


def registrable_domain(host: str) -> str:
    labels = host.rstrip(".").split(".")
    return ".".join(labels[-2:])


def solve(ctx) -> SolveResult:  # type: ignore[no-untyped-def]
    expected = ctx.expected_flags["read-the-headers"]
    with httpx.Client(base_url=ctx.url(), timeout=10) as client:
        raw = client.get("/evidence/mail.eml").content

    msg = BytesParser(policy=policy.default).parsebytes(raw)
    from_domain = str(msg.get("From")).rsplit("@", 1)[1].rstrip(">").strip().lower()
    return_path_domain = str(msg.get("Return-Path")).rsplit("@", 1)[1].rstrip(">").strip().lower()

    body = msg.get_body(preferencelist=("plain",))
    text = body.get_content() if body else msg.get_payload()
    match = re.search(r"https://([^/\s]+)", text)
    if not match:
        return SolveResult(
            results=[
                TaskResult(task_id="read-the-headers", ok=False, detail="no URL found in body")
            ]
        )
    link_domain = registrable_domain(match.group(1))

    res = client_post_quiz(ctx, from_domain, return_path_domain, link_domain)
    captured = res if res and find_flags(res) else None
    ok = captured == expected
    detail = (
        None
        if ok
        else f"quiz answers rejected: {from_domain=} {return_path_domain=} {link_domain=}"
    )
    return SolveResult(
        results=[TaskResult(task_id="read-the-headers", ok=ok, captured=captured, detail=detail)]
    )


def client_post_quiz(ctx, from_domain: str, return_path_domain: str, link_domain: str):  # type: ignore[no-untyped-def]
    with httpx.Client(base_url=ctx.url(), timeout=10) as client:
        res = client.post(
            "/quiz",
            json={
                "from_domain": from_domain,
                "return_path_domain": return_path_domain,
                "link_domain": link_domain,
            },
        )
    return res.json().get("flag") if res.is_success else None
