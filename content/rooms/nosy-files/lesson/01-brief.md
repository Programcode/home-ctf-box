# Nosy Files

DocVault serves office notes through a download endpoint that glues
whatever name it receives onto its document directory. You will treat
that behavior as evidence, climb out of the document root with
traversal sequences, and read a deployment record the service stores
outside the folder it publishes.

## What you will practice

- Confirming unserved paths exist by comparing listed files with the
  endpoint's response shape.
- Writing `../` traversal sequences that escape a base directory.
- Reading files the application never linked, then capturing the
  per-session flag from one of them.

## Scope

Only the portal at `http://target:8000` is in scope. Nothing outside
your lab instance is a target.
