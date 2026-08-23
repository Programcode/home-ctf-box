# Double Trouble

Cartly's checkout has a coupon guard: anything above 50 percent is
rejected. The guard and the arithmetic, though, read the discount
parameter from different places in the query string. One request with
the parameter named twice satisfies the guard with the first value and
bills with the second. You will find the split, drive the total below
zero, and take the refund reference the order page prints.

## What you will practice

- Sending repeated query parameters and observing which copy each code
  path reads.
- Turning a validation-versus-calculation mismatch into a negative
  balance.
- Confirming the exploit by capturing the per-session flag.

## Scope

Only the shop at `http://target:8000` is in scope. Nothing outside your
lab instance is a target.
