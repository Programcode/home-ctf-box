# IDOR Invoices

Ledgerly is a small invoicing tool on your lab network. You are signed
in as one employee, and the dashboard lists your three invoices. The
handler behind `/invoice/<number>` loads whatever record the URL names,
with no check that the number belongs to you. You will read the
identifier pattern from your own bills, step to a record the app never
linked, and take the internal release code printed on another
customer's invoice.

## What you will practice

- Reading URL structure to learn how the application identifies records.
- Predicting and requesting an object reference outside your account.
- Recognizing broken object-level authorization from what comes back.

## Scope

Only the invoicing app at `http://target:8000` is in scope. Nothing
outside your lab instance is a target. The dataset is static and
fictional.
