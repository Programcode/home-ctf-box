# Cache Me Outside

Signal Harbor ingests telemetry from small satellite fleets, and its
status board sits behind an edge page cache. The cache decides what it
stores using the request path alone, while the renderer reads host
routing headers to decide how the page should look. Internal virtual
hosts get verbose diagnostics. If you can convince the renderer once,
everyone gets your copy until the entry expires.

## What you will practice

- Telling apart what a cache keys on from what a renderer reacts to.
- Using X-Forwarded-Host to impersonate an internal virtual host at the application layer.
- Confirming a poisoning worked by reading the page exactly the way a normal visitor would.

## Scope

Only the site at `http://target:8000` is in scope. Nothing outside
your lab instance is a target.
