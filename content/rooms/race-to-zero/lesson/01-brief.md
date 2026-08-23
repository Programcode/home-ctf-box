# Race to Zero

Meridian Pay runs a payments sandbox where every account starts at
1000.00 EUR. The withdrawals API looks boring until you look between
its steps: a worker reads your balance, the fraud scorer thinks about
it, and only then does the debit land. Two transfers that overlap inside
that gap never see each other's money.

## What you will practice

- Reading a decline response as documentation of where the check happens.
- Turning a read-then-write window into an exploit with concurrent requests.
- Proving the race by reading state afterward: the account settles below zero.

## Scope

Only the bank at `http://target:8000` is in scope. Nothing outside
your lab instance is a target.
