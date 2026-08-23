"""Gateway simulator: metrics leak, deliberate routing. Room target only."""

from html import escape
import os

from flask import Flask, Response, request

app = Flask(__name__)
FLAG = os.environ["ROOM_FLAG"]

LOCAL_DEV = "eth0"
REMOTE_DEV = "tunsim0"
ROUTES = (
    ("eth0", "10.60.0.0/24", "local operations segment"),
    ("podnet0", "172.20.0.0/24", "simulated container bridge"),
    (REMOTE_DEV, "10.70.99.0/24", "tunnel to remote segment"),
)

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>{title}</title>
<style>
body {{ background:#F7F6F3; font-family:Helvetica,Arial,sans-serif; display:flex; justify-content:center; padding-top:12vh; }}
.box {{ background:#fff; border:1px solid #EAEAEA; border-radius:8px; padding:2.5rem; width:30rem; }}
h1 {{ letter-spacing:-0.02em; font-size:1.4rem; margin-bottom:1rem; }}
p, li {{ color:#787774; font-size:.9rem; line-height:1.5; }}
code, pre {{ background:#F7F6F3; padding:.1rem .35rem; border-radius:4px; font-size:.85rem; }}
pre {{ padding:1rem; overflow:auto; }}
.flag {{ background:#EDF3EC; color:#346538; border-radius:9999px; padding:.35rem 1rem; display:inline-block; }}
</style></head><body>{body}</body></html>"""


def _page(title: str, body: str, status: int = 200) -> Response:
    return Response(PAGE.format(title=title, body=body), status=status)


@app.get("/healthz")
def healthz():
    return "ok"


@app.get("/")
def home():
    return _page(
        "Segment gateway",
        """
<div class="box">
<h1>Segment gateway</h1>
<p>This host fronts the lab's simulated router fabric.</p>
<p><code>GET /metrics</code> exports the interface table in
Prometheus text format.</p>
<p><code>POST /route</code> with JSON
<code>{"subnet": "a.b.c.d/nn"}</code> steers a probe toward the named
segment and returns whatever that segment serves.</p>
<p>Enumerate before you steer. Wrong subnets fail closed with an
explanation.</p>
</div>""",
    )


@app.get("/metrics")
def metrics():
    lines = [
        "# HELP routesim_route simulated interface route table",
        "# TYPE routesim_route gauge",
    ]
    for dev, dest, note in ROUTES:
        lines.append(f"# route note for {dev}: {note}")
        lines.append(f'routesim_route{{dev="{dev}",dest="{dest}"}} 1')
    return Response("\n".join(lines) + "\n", mimetype="text/plain; version=0.0.4")


@app.post("/route")
def route():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        data = {}
    subnet = str(data.get("subnet") or request.form.get("subnet") or "").strip()
    if not subnet:
        return _page(
            "Route refused",
            """
<div class="box">
<h1>Route refused</h1>
<p>No subnet supplied. POST JSON like
<code>{"subnet": "10.70.99.0/24"}</code>.</p>
</div>""",
            400,
        )
    match = next(((dev, dest, note) for dev, dest, note in ROUTES if dest == subnet), None)
    if match is None:
        known = ", ".join(dest for _d, dest, _n in ROUTES)
        return _page(
            "No such segment",
            f"""
<div class="box">
<h1>No such segment</h1>
<p>The gateway has no interface serving <code>{escape(subnet)}</code>. Known
segments are <code>{known}</code>; the metrics endpoint explains what
each one is.</p>
</div>""",
            404,
        )
    dev, dest, note = match
    if dev == LOCAL_DEV:
        return _page(
            "Already home",
            """
<div class="box">
<h1>That is the local segment</h1>
<p>You are already on it; routing here loops back to the gateway you
are talking to. Look for the interface whose note mentions a
tunnel.</p>
</div>""",
            404,
        )
    if dev == REMOTE_DEV:
        return _page(
            f"Remote segment {dest}",
            f"""
<div class="box">
<h1>Reply from remote segment {dest}</h1>
<p>Delivered via <code>{dev}</code> ({note}). The segment node reports:</p>
<pre>segment status: isolated
last operator note: keep the tunnel credentials off the local segment
session secret: {FLAG}</pre>
<span class="flag">{FLAG}</span>
</div>""",
        )
    return _page(
        f"Segment {dest} reached",
        f"""
<div class="box">
<h1>Segment {dest}</h1>
<p>The {note} acknowledges the probe. There is nothing of value on
this segment; the objective lives behind the tunnel interface.</p>
</div>""",
        404,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, threaded=True)
