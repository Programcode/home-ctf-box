# Mass Assign

Nimbus runs a people API where a profile patch is merged straight into
storage, key for key. The official client sends name and email, but the
endpoint copies whatever else arrives too. You will push a role claim
through the merge, then read the note the API reserves for admins.

## What you will practice

- Comparing what an API accepts against what its client normally sends.
- Abusing a bulk update to write a field you should not control.
- Confirming the privilege change by capturing the per-session flag.

## Scope

Only the API at `http://target:8000` is in scope. Nothing outside your
lab instance is a target.
