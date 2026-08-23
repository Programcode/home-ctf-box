# Tenant Trouble

Ledgerline is a multi-tenant invoicing platform, and your lab instance
signs you in as the Acme Corp demo workspace. Somewhere on the same
ledger sit the books of Globex Ltd, including one audit invoice with a
reconciliation note nobody outside Globex should ever read. You will
find the seam between the tenants and read it anyway.

## What you will practice

- Asking which request element carries identity, then testing whether you control it.
- Harvesting identifiers from public pages: workspace slugs, invoice
  number ranges, and the numbering policy itself.
- Recognizing an authorization check that compares against attacker-supplied input.

## Scope

Only the platform at `http://target:8000` is in scope. Nothing outside
your lab instance is a target.
