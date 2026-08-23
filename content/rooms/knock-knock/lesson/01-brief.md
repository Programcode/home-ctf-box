# Knock Knock

Harborview Records keeps its archive behind a timed gate. The web
endpoint exists, but it stays sealed until the gatekeeper daemon over
UDP announces a valid visitor. Real networks use this pattern to keep
administrative services invisible to drive-by scanners: nothing answers
on TCP until you prove you know the secret rhythm.

## What you will practice

- Treating UDP as a first-class reconnaissance target instead of an
  afterthought. A closed TCP port tells you nothing about a service
  that only speaks datagrams.
- Holding state across several packets: each knock advances a counter
  the server keeps, and the order plus timing decide whether it
  accepts you.
- Reading a protocol from its replies alone. The status probe on
  udp/9999 explains the rules in plain text if you ask it anything,
  which is exactly how undocumented services get documented in the
  field.

The vault token you earn lasts sixty seconds. That deadline matters:
port knocking in production pairs with short-lived firewall windows,
so tools chain the knocks and the follow-up connection in one run. You
will do the same with a small Python script using only the standard
library socket module.

## Scope

Only the appliance at `http://target:8000` and its UDP ports 7000,
8000, 9000, and 9999 are in scope. Nothing outside your lab instance
is a target. A successful sequence merely flips an in-memory switch in
this container; no system firewall or host state changes.
