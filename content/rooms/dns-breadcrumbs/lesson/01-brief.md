# DNS Breadcrumbs

Every network that names its own machines leaves a map lying around,
and the map is DNS. The lab.internal zone on this target follows a
naming convention you can read at a glance: portal, files, wiki, each
with an address record pointing into 10.60.0.0/24. One subdomain goes
further and keeps operations notes in a TXT record, which is exactly
the kind of habit that leaks secrets slowly.

## What you will practice

- Speaking DNS by hand. A query is twelve header bytes, then the name
  written as length-prefixed labels, then qtype and qclass. You will
  pack that with struct, send it to udp/53, and decode the reply
  yourself, including compression pointers in answer sections.
- Reading record types as signals. Type 1 is an address, type 16 is
  free-form text, type 255 asks for anything a name holds, and type
  252 asks the server to hand over the whole zone.
- Recognizing a misconfiguration when you see one. Zone transfers are
  meant for secondary servers; when an authoritative responder answers
  AXFR from anyone, every naming decision, note, and comment in the
  zone becomes public inside the network.

The intended path tries AXFR first and ANY as fallback, mirroring how
a careful assessor confirms findings before writing them up.

## Scope

Only `http://target:8000` and the resolver on udp/tcp 53 of the same
host are in scope. Nothing outside your lab instance is a target. The
server runs as uid 10001 in a disposable container; port 53 binding is
the single capability it holds.
