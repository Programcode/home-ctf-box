"""lab.internal authoritative responder plus case notes. Room target only."""

import os

from dnslib import A, NS, RR, SOA, TXT, QTYPE
from dnslib.server import BaseResolver, DNSServer
from flask import Flask

app = Flask(__name__)
FLAG = os.environ["ROOM_FLAG"]

ZONE = "lab.internal."
ZONE_RECORDS = [
    RR(
        ZONE,
        QTYPE.SOA,
        rdata=SOA(
            "ns1.lab.internal.", "hostmaster.lab.internal.", (2026082301, 3600, 600, 86400, 300)
        ),
        ttl=300,
    ),
    RR(ZONE, QTYPE.NS, rdata=NS("ns1.lab.internal."), ttl=300),
    RR("ns1.lab.internal.", QTYPE.A, rdata=A("10.60.0.53"), ttl=300),
    RR("portal.lab.internal.", QTYPE.A, rdata=A("10.60.0.10"), ttl=300),
    RR("files.lab.internal.", QTYPE.A, rdata=A("10.60.0.11"), ttl=300),
    RR("wiki.lab.internal.", QTYPE.A, rdata=A("10.60.0.12"), ttl=300),
    RR("flag.lab.internal.", QTYPE.TXT, rdata=TXT(FLAG), ttl=300),
]


class LabResolver(BaseResolver):
    def resolve(self, request, _handler):  # type: ignore[no-untyped-def]
        reply = request.reply()
        qname = request.q.qname
        qtype = request.q.qtype
        if qtype == QTYPE.AXFR:
            for record in ZONE_RECORDS:
                reply.add_answer(record)
            return reply
        for record in ZONE_RECORDS:
            if record.rname == qname and qtype in (QTYPE.ANY, record.rtype):
                reply.add_answer(record)
        return reply


PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>lab.internal name service</title>
<style>
body { background:#F7F6F3; font-family:Helvetica,Arial,sans-serif; display:flex; justify-content:center; padding-top:12vh; }
.box { background:#fff; border:1px solid #EAEAEA; border-radius:8px; padding:2.5rem; width:30rem; }
h1 { letter-spacing:-0.02em; font-size:1.4rem; margin-bottom:1rem; }
p, li { color:#787774; font-size:.9rem; line-height:1.5; }
code { background:#F7F6F3; padding:.1rem .35rem; border-radius:4px; font-size:.85rem; }
</style></head><body>%s</body></html>"""


@app.get("/healthz")
def healthz():
    return "ok"


@app.get("/")
def home():
    return (
        PAGE
        % """
<div class="box">
<h1>lab.internal name service</h1>
<p>This host runs the authoritative resolver for the
<code>lab.internal</code> zone on port 53, UDP and TCP.</p>
<p>Address records in this zone follow an internal naming convention.
The operations team also keeps plain-text notes in TXT records, and a
spot check suggests transfer restrictions were never configured.</p>
<p>Ask the server yourself; this page is only the reception desk.</p>
</div>"""
    )


if __name__ == "__main__":
    resolver = LabResolver()
    DNSServer(resolver, port=53, address="0.0.0.0").start_thread()
    DNSServer(resolver, port=53, address="0.0.0.0", tcp=True).start_thread()
    app.run(host="0.0.0.0", port=8000, threaded=True)
